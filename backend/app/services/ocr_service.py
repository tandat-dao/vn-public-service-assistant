"""OCR service — two-path pipeline for identity document extraction.

Path A (QR decode): 5-attempt pyzbar decode with OpenCV pre-processing.
  Returns PersonalData with confidence=1.0 on success (~200ms, zero LLM tokens).

Path B (OCR + LLM): OpenCV preprocessing → PaddleOCR → pre-filter → LLM extraction.
  Always used for non-CCCD documents; also the CCCD fallback when QR fails.

System dependency: pyzbar requires the libzbar0 native library.
  Linux: sudo apt-get install libzbar0
  Windows: bundled with the pyzbar wheel for common architectures.

PaddleOCR is synchronous — NEVER call it directly in an async function.
Always wrap in asyncio.get_running_loop().run_in_executor(None, self._run_paddle_ocr, path).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from datetime import date, datetime
from typing import Any

import cv2
import structlog

from app.agents.prompts.document_classifier_prompt import (
    CLASSIFIER_SYSTEM_PROMPT,
    VALID_DOCUMENT_TYPES,
    build_classifier_messages,
)
from app.agents.prompts.ocr_extraction_prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_messages,
)
from app.config import settings
from app.schemas.personal_data import Address, PersonalData

# Imported at module level so tests can patch app.services.ocr_service.pyzbar_decode
from pyzbar.pyzbar import decode as pyzbar_decode

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Provenance fields — excluded from field_confidences population
# ---------------------------------------------------------------------------
_PROVENANCE_FIELDS = frozenset(
    {
        "source_document_type",
        "source_image_path",
        "extraction_confidence",
        "extracted_at",
        "field_confidences",
        "nationality",
        "raw_address",   # raw source string — not a semantic extraction field
    }
)


# ---------------------------------------------------------------------------
# Pure helper functions (module-level for easy unit testing)
# ---------------------------------------------------------------------------

def _validate_id_number(id_num: str) -> str | None:
    """Return id_num if 12-digit numeric with province code 1–CCCD_PROVINCE_CODE_MAX."""
    if not id_num or not id_num.isdigit() or len(id_num) != 12:
        return None
    province = int(id_num[:3])
    if province < 1 or province > settings.CCCD_PROVINCE_CODE_MAX:
        return None
    return id_num


def _parse_ddmmyyyy(s: str) -> date | None:
    """Parse DDMMYYYY string to date. Returns None on any error."""
    if not s:
        return None
    s = s.strip()
    if len(s) < 8:
        return None
    try:
        return datetime.strptime(s[:8], "%d%m%Y").date()
    except ValueError:
        return None


def _compute_iou(bbox1: list, bbox2: list) -> float:
    """IoU between two 4-point bounding boxes (axis-aligned approximation)."""
    def to_rect(bbox: list) -> tuple[float, float, float, float]:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return min(xs), min(ys), max(xs), max(ys)

    x1a, y1a, x2a, y2a = to_rect(bbox1)
    x1b, y1b, x2b, y2b = to_rect(bbox2)

    ix1, iy1 = max(x1a, x1b), max(y1a, y1b)
    ix2, iy2 = min(x2a, x2b), min(y2a, y2b)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (x2a - x1a) * (y2a - y1a)
    area_b = (x2b - x1b) * (y2b - y1b)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# OCRService
# ---------------------------------------------------------------------------

class OCRService:
    """Two-path OCR pipeline: QR decode (primary) + PaddleOCR/LLM (fallback)."""

    def __init__(self, llm_service: Any | None = None) -> None:
        if llm_service is None:
            from app.services.llm import LLMService
            llm_service = LLMService()
        self._llm = llm_service
        self._paddle_engine: Any = None  # lazy-initialised on first use

    # ------------------------------------------------------------------
    # Lazy PaddleOCR init
    # ------------------------------------------------------------------

    def _get_paddle_engine(self) -> Any:
        if self._paddle_engine is None:
            from paddleocr import PaddleOCR  # lazy import — avoids slow startup
            self._paddle_engine = PaddleOCR(
                use_angle_cls=True,
                lang=settings.PADDLEOCR_LANG,
                use_gpu=settings.PADDLEOCR_USE_GPU,
                show_log=False,
            )
        return self._paddle_engine

    # ------------------------------------------------------------------
    # Sub-component A: QR decode path
    # ------------------------------------------------------------------

    async def decode_qr(self, image_path: str) -> PersonalData | None:
        """Attempt QR decode with 5 pre-processing variants.

        Returns PersonalData (confidence=1.0) on success, None if all fail.
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.warning("decode_qr: cannot read image", path=image_path)
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Try to locate QR region for focused upscaling
        detector = cv2.QRCodeDetector()
        detected, qr_pts = detector.detect(gray)

        if detected and qr_pts is not None:
            pts = qr_pts.astype(int).reshape(-1, 2)
            x, y, w, h = cv2.boundingRect(pts)
            margin = max(10, int(min(w, h) * 0.1))
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(gray.shape[1], x + w + margin)
            y2 = min(gray.shape[0], y + h + margin)
            roi = gray[y1:y2, x1:x2]
            upscaled = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        else:
            upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

        def _thresh(src: Any) -> Any:
            return cv2.adaptiveThreshold(
                src, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        attempts = [
            _thresh(gray),                                                   # 1: full, thresh
            _thresh(upscaled),                                               # 2: upscaled, thresh
            _thresh(cv2.GaussianBlur(upscaled, (3, 3), 0)),                  # 3: upscaled + blur
            _thresh(cv2.morphologyEx(upscaled, cv2.MORPH_CLOSE, kernel)),    # 4: upscaled + close
            _thresh(cv2.bitwise_not(gray)),                                  # 5: inverted
        ]

        for attempt_img in attempts:
            results = pyzbar_decode(attempt_img)
            for result in results:
                parsed = self._parse_qr_data(result.data, image_path)
                if parsed is not None:
                    return parsed

        logger.info("decode_qr: all 5 attempts failed", path=image_path)
        return None

    def _parse_qr_data(self, raw_bytes: bytes, image_path: str) -> PersonalData | None:
        """Parse pipe-delimited CCCD QR bytes into PersonalData."""
        try:
            text = raw_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return None

        parts = text.split("|")
        if len(parts) < 7:
            logger.warning("decode_qr: unexpected QR field count", count=len(parts))
            return None

        # Format: id_number||full_name|dob|gender|address|issue_date
        # Index 1 is always empty — never mapped to any field
        id_num_raw = parts[0].strip()
        # parts[1] intentionally skipped
        full_name = parts[2].strip() or None
        dob_str = parts[3].strip()
        gender_raw = parts[4].strip()
        address_str = parts[5].strip() or None
        issue_date_str = parts[6].strip()

        # Validate id_number
        id_number = _validate_id_number(id_num_raw)
        if id_num_raw and id_number is None:
            logger.warning(
                "decode_qr: invalid id_number format — set to None",
                raw_id=id_num_raw,
            )

        dob = _parse_ddmmyyyy(dob_str)
        issue_date = _parse_ddmmyyyy(issue_date_str)

        # Normalise gender
        gender_lower = gender_raw.lower()
        gender: str | None
        if gender_lower in ("nam", "male", "m"):
            gender = "Nam"
        elif gender_lower in ("nữ", "nu", "female", "f", "nü"):
            gender = "Nữ"
        else:
            gender = None

        # Parse structured address from QR string.
        # Vietnamese format (most-specific → least-specific): street, ward, district, city
        # Split on ", " (comma-space). Fewer than 4 segments → fallback to street-only.
        parsed_address: Address | None = None
        if address_str:
            segments = address_str.split(", ")
            if len(segments) >= 4:
                city = segments[-1]
                district = segments[-2]
                ward = segments[-3]
                street = ", ".join(segments[:-3])
                parsed_address = Address(
                    street=street, ward=ward, district=district, city=city
                )
            else:
                logger.debug(
                    "decode_qr: address has fewer than 4 components, using raw string as street",
                    component_count=len(segments),
                )
                parsed_address = Address(street=address_str)

        field_map = {
            "id_number": id_number,
            "full_name": full_name,
            "date_of_birth": dob,
            "gender": gender,
            "permanent_address": address_str,
            "id_issue_date": issue_date,
        }
        field_confidences = {k: 1.0 for k, v in field_map.items() if v is not None}

        return PersonalData(
            full_name=full_name,
            date_of_birth=dob,
            gender=gender,  # type: ignore[arg-type]
            id_number=id_number,
            id_issue_date=issue_date,
            permanent_address=parsed_address,
            raw_address=address_str,
            source_document_type="cccd",
            source_image_path=image_path,
            extraction_confidence=1.0,
            field_confidences=field_confidences,
            extracted_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Sub-component B: Document type classifier
    # ------------------------------------------------------------------

    async def classify_document_type(self, image_path: str) -> str:
        """Vision LLM call — returns one of the 5 VALID_DOCUMENT_TYPES strings.

        Never raises. Falls back to "other" on any error or unexpected response.
        """
        try:
            with open(image_path, "rb") as fh:
                image_bytes = fh.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            messages = build_classifier_messages(image_b64, image_path)
            raw = await self._llm.async_invoke(
                system=CLASSIFIER_SYSTEM_PROMPT,
                messages=messages,
                max_tokens=16,
            )
            doc_type = raw.strip().lower()
            if doc_type not in VALID_DOCUMENT_TYPES:
                logger.warning(
                    "classify_document_type: unexpected value, using 'other'",
                    raw_value=raw,
                )
                return "other"
            return doc_type
        except Exception as exc:
            logger.warning("classify_document_type: failed", error=str(exc))
            return "other"

    # ------------------------------------------------------------------
    # Sub-component D: PaddleOCR pre-filter (pure synchronous)
    # ------------------------------------------------------------------

    def _filter_ocr_results(self, raw_results: list) -> list:
        """Filter PaddleOCR detections: low confidence, short text, IoU duplicates.

        Args:
            raw_results: Output from paddleocr_engine.ocr() — list structure may
                         be nested: [[bbox, (text, confidence)], ...].
        Returns:
            Filtered list with the same element structure.
        """
        if not raw_results:
            return []

        # PaddleOCR wraps results in an outer page list: [[det1, det2, ...]].
        # Detect this by checking 4 levels deep: in the nested format,
        # detections[0][0][0][0] is a point [x, y] (a list); in the flat
        # format detections[0][0][0][0] is a raw number coordinate.
        detections = raw_results
        if (
            detections
            and isinstance(detections[0], list)
            and detections[0]
            and isinstance(detections[0][0], list)
            and detections[0][0]
            and isinstance(detections[0][0][0], list)
            and detections[0][0][0]
            and isinstance(detections[0][0][0][0], list)
        ):
            detections = detections[0]

        filtered: list = []
        for det in detections:
            if not det or len(det) < 2:
                continue
            bbox, text_conf = det[0], det[1]
            if not isinstance(text_conf, (tuple, list)) or len(text_conf) < 2:
                continue
            text, conf = str(text_conf[0]), float(text_conf[1])

            if conf < settings.OCR_CONFIDENCE_THRESHOLD:
                continue
            if len(text.strip()) < settings.OCR_MIN_TEXT_LENGTH:
                continue

            filtered.append(det)

        # IoU deduplication — O(n²), OCR result lists are small
        keep = [True] * len(filtered)
        for i in range(len(filtered)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(filtered)):
                if not keep[j]:
                    continue
                iou = _compute_iou(filtered[i][0], filtered[j][0])
                if iou > 0.5:
                    conf_i = float(filtered[i][1][1])
                    conf_j = float(filtered[j][1][1])
                    if conf_i >= conf_j:
                        keep[j] = False
                    else:
                        keep[i] = False
                        break

        return [det for det, k in zip(filtered, keep) if k]

    # ------------------------------------------------------------------
    # OpenCV pre-processing helpers
    # ------------------------------------------------------------------

    def _deskew(self, gray: Any) -> Any:
        """Correct image skew within ±OCR_DESKEW_MAX_DEGREES."""
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        coords = cv2.findNonZero(binary)
        if coords is None or len(coords) < 10:
            return gray

        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > settings.OCR_DESKEW_MAX_DEGREES:
            logger.debug("deskew: angle too large, skipping", angle=angle)
            return gray
        if abs(angle) < 0.1:
            return gray

        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(
            gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    def _preprocess_for_ocr(self, image_path: str) -> str:
        """Apply CLAHE → deskew → denoise. Writes result to temp file.

        Returns temp file path. Caller is responsible for cleanup (os.unlink).
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(
            clipLimit=settings.OCR_CLAHE_CLIP_LIMIT,
            tileGridSize=(8, 8),
        )
        enhanced = clahe.apply(gray)
        deskewed = self._deskew(enhanced)
        denoised = cv2.fastNlMeansDenoising(deskewed, h=settings.OCR_DENOISE_H)

        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp_path = tmp.name
        tmp.close()
        cv2.imwrite(tmp_path, denoised)
        return tmp_path

    # ------------------------------------------------------------------
    # Sync PaddleOCR wrapper — always call via run_in_executor
    # ------------------------------------------------------------------

    def _run_paddle_ocr(self, image_path: str) -> list:
        """Synchronous PaddleOCR call. MUST be invoked via run_in_executor."""
        return self._get_paddle_engine().ocr(image_path, cls=True) or []

    # ------------------------------------------------------------------
    # Sub-component E: Full OCR extraction path
    # ------------------------------------------------------------------

    async def extract(self, image_path: str, document_type: str) -> PersonalData:
        """OCR path: preprocess → PaddleOCR (executor) → filter → LLM extraction.

        Never raises. Returns an empty PersonalData (all fields None) on failure.
        """
        preprocessed_path: str | None = None
        try:
            loop = asyncio.get_running_loop()

            preprocessed_path = await loop.run_in_executor(
                None, self._preprocess_for_ocr, image_path
            )

            raw_results = await loop.run_in_executor(
                None, self._run_paddle_ocr, preprocessed_path
            )

            filtered = self._filter_ocr_results(raw_results)

            text_lines = [
                str(det[1][0]) for det in filtered if str(det[1][0]).strip()
            ]
            joined_text = "\n".join(text_lines)

            estimated_tokens = len(joined_text) // 4
            if estimated_tokens > settings.OCR_RAW_TOKEN_CAP:
                cap_chars = settings.OCR_RAW_TOKEN_CAP * 4
                logger.warning(
                    "OCR text truncated",
                    original_tokens=estimated_tokens,
                    cap_tokens=settings.OCR_RAW_TOKEN_CAP,
                )
                joined_text = joined_text[:cap_chars]

            messages = build_extraction_messages(joined_text, document_type)
            raw_response = await self._llm.async_invoke(
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=messages,
                max_tokens=512,
            )

            return self._parse_extraction_response(
                raw_response, image_path, document_type, filtered
            )

        except Exception as exc:
            logger.warning("extract: unexpected error", error=str(exc))
            return PersonalData(
                source_document_type=document_type,
                source_image_path=image_path,
                extraction_confidence=0.0,
                extracted_at=datetime.utcnow(),
            )
        finally:
            if preprocessed_path:
                try:
                    os.unlink(preprocessed_path)
                except OSError:
                    pass

    def _parse_extraction_response(
        self,
        raw_response: str,
        image_path: str,
        document_type: str,
        filtered_detections: list,
    ) -> PersonalData:
        """Parse LLM JSON response into PersonalData. Returns empty PD on failure."""
        mean_conf = (
            sum(float(d[1][1]) for d in filtered_detections) / len(filtered_detections)
            if filtered_detections
            else 0.5
        )
        
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                import re
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned.strip())
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "extract: JSON parse failed",
                error=str(exc),
                raw_preview=raw_response[:120],
            )

        # Coerce plain string addresses to Address-compatible dicts
        for addr_field in ("permanent_address", "temporary_address"):
            if addr_field in data and isinstance(data[addr_field], str):
                data[addr_field] = {"street": data[addr_field]}

        data["source_document_type"] = document_type
        data["source_image_path"] = image_path
        data["extraction_confidence"] = mean_conf
        data["extracted_at"] = datetime.utcnow().isoformat()
        data.setdefault("field_confidences", {})

        try:
            pd_obj = PersonalData.model_validate(data)
        except Exception as exc:
            logger.warning("extract: PersonalData validation failed", error=str(exc))
            return PersonalData(
                source_document_type=document_type,
                source_image_path=image_path,
                extraction_confidence=0.0,
                extracted_at=datetime.utcnow(),
            )

        # Populate field_confidences for every non-null content field
        field_confs = {
            k: mean_conf
            for k, v in pd_obj.model_dump().items()
            if v is not None and k not in _PROVENANCE_FIELDS
        }
        return pd_obj.model_copy(update={"field_confidences": field_confs})
