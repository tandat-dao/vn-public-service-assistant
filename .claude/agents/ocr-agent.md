# OCR Agent — Behavioural Specification

## Node: `ocr_node`
## File: `app/agents/nodes/ocr.py`
## Prompt: `app/agents/prompts/ocr_extraction_prompt.py`

## Responsibility
Run the full OCR pipeline on an uploaded document image and populate PersonalData.
Only this node calls `ocr_service` and `storage_service`.

## Inputs (read from AgentState)
- `uploaded_image_path: str` — must be present (router only sends here if image exists)
- `session_id: str` — to load existing PersonalData for merging

## Outputs (partial AgentState dict)
- `personal_data: PersonalData`
- `document_type: str` — classified document type

## Processing Pipeline (execute in this exact order — no steps optional)
1. Download image from MinIO via `storage_service`
2. OpenCV pre-processing: deskew → CLAHE → denoise
3. Classify document type via vision LLM
4. Run PaddleOCR (Vietnamese PP-OCRv4)
5. LLM field extraction using `ocr_extraction_prompt`
6. Validation: CCCD checksum if applicable, date normalisation always
7. Load existing PersonalData from session (Redis)
8. Merge with `session_accumulator.merge()` — higher confidence wins
9. Return merged PersonalData

## Field Extraction Rules
- The extraction prompt must instruct the model to return `null` for unrecognised fields — never guess
- Fields with confidence < 0.5 must be set to `None` even if text was extracted
- `extraction_confidence` = mean of all `field_confidences` values

## Fallback
PaddleOCR fails → retry once with Tesseract.
Both fail → set `personal_data = None`, append error, continue — do not crash.
