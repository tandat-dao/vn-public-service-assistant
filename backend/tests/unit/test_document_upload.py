"""Unit tests for POST /api/v1/documents/upload.

Strategy:
- Build a minimal FastAPI app (no lifespan, no SlowAPIMiddleware) to avoid
  MinIO/Redis startup deps and shared rate-limit counter accumulation.
  Rate-limit behaviour is already covered by test_rate_limiting.py.
- Patch _get_storage, _get_ocr, _get_redis singletons to return AsyncMocks.
- Patch validate_upload to a no-op coroutine in most tests.
- All OCR, storage, and Redis calls are mocked — no real MinIO, no PaddleOCR.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.rate_limit import limiter as _prod_limiter  # needed to bypass rate limit in tests
from app.schemas.personal_data import PersonalData
from app.schemas.session import SessionData

# ---------------------------------------------------------------------------
# Minimal non-empty upload payload.
# Not a valid JPEG but enough for tests where magic/OCR are mocked.
# ---------------------------------------------------------------------------
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\xff\xd9"
)


def _make_personal_data(
    full_name: str = "Nguyễn Văn A",
    conf_full_name: float = 0.9,
    conf_id: float = 0.8,
) -> PersonalData:
    return PersonalData(
        full_name=full_name,
        id_number="001234567890",
        source_document_type="cccd",
        source_image_path="/tmp/test.jpg",
        extraction_confidence=(conf_full_name + conf_id) / 2,
        field_confidences={"full_name": conf_full_name, "id_number": conf_id},
        extracted_at=datetime.utcnow(),
    )


def _make_test_app() -> FastAPI:
    """Build a minimal FastAPI app without rate-limit middleware.

    Rate limiting is already covered by test_rate_limiting.py.
    Omitting SlowAPIMiddleware prevents the shared in-memory rate-limit counter
    from accumulating across tests and triggering spurious 429s on tests 6+.
    """
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield  # skip MinIO / Redis / OCR startup

    from app.api.v1.router import router as v1_router

    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(v1_router, prefix="/api/v1")
    return app


def _make_mocks(
    ocr_decode_qr_result: PersonalData | None = None,
    ocr_extract_result: PersonalData | None = None,
    storage_upload_raises: Exception | None = None,
    redis_get_result: SessionData | None = None,
    redis_save_raises: Exception | None = None,
) -> tuple:
    """Build mock storage, ocr, and redis objects for a test scenario."""
    mock_storage = MagicMock()
    if storage_upload_raises:
        mock_storage.upload = AsyncMock(side_effect=storage_upload_raises)
    else:
        mock_storage.upload = AsyncMock(return_value="tmp/sess/abc.jpg")

    mock_ocr = MagicMock()
    mock_ocr.decode_qr = AsyncMock(return_value=ocr_decode_qr_result)
    mock_ocr.classify_document_type = AsyncMock(return_value="cccd")
    mock_ocr.extract = AsyncMock(
        return_value=ocr_extract_result or _make_personal_data()
    )

    mock_redis = MagicMock()
    mock_redis.get_session = AsyncMock(return_value=redis_get_result)
    if redis_save_raises:
        mock_redis.save_session = AsyncMock(side_effect=redis_save_raises)
    else:
        mock_redis.save_session = AsyncMock(return_value=None)

    return mock_storage, mock_ocr, mock_redis


def _upload_jpeg(client: TestClient, session_id: str = "test-session") -> object:
    return client.post(
        "/api/v1/documents/upload",
        files={"file": ("photo.jpg", MINIMAL_JPEG, "image/jpeg")},
        data={"session_id": session_id},
    )


def _bypass_rate_limit():
    """Disable the production limiter for a test.

    The @limiter.limit() decorator captures the limiter object in its closure.
    Patching the module-level name has no effect. Patching only _check_request_limit
    leaves request.state.view_rate_limit unset, causing an AttributeError in
    slowapi's header-injection step. Setting `enabled=False` disables BOTH the
    rate-check path AND the header-injection path in the async_wrapper, avoiding
    any 500s from unset request state. Rate-limit behaviour is tested separately in
    test_rate_limiting.py.
    """
    return patch.object(_prod_limiter, "enabled", new=False)


# ---------------------------------------------------------------------------
# Test 1 — Valid JPEG + QR decode succeeds → success response with personal_data
# ---------------------------------------------------------------------------

class TestUploadValidJpegReturnsSuccess:
    def test_upload_valid_jpeg_returns_success(self):
        app = _make_test_app()
        personal_data = _make_personal_data()
        mock_storage, mock_ocr, mock_redis = _make_mocks(
            ocr_decode_qr_result=personal_data,
        )

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = _upload_jpeg(client)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["personal_data"] is not None
        assert body["personal_data"]["full_name"] == "Nguyễn Văn A"
        assert body["ocr_confidence"] > 0.0
        assert "tmp_path" in body


# ---------------------------------------------------------------------------
# Test 2 — OCR failure (both paths raise) → 200 partial response
# ---------------------------------------------------------------------------

class TestUploadOcrFailureReturnsPartial:
    def test_upload_ocr_failure_returns_partial(self):
        app = _make_test_app()
        mock_storage, mock_ocr, mock_redis = _make_mocks()
        mock_ocr.decode_qr = AsyncMock(return_value=None)
        mock_ocr.classify_document_type = AsyncMock(
            side_effect=RuntimeError("paddle crash")
        )

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = _upload_jpeg(client)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "partial"
        assert body["personal_data"] is None
        assert body["ocr_confidence"] == 0.0


# ---------------------------------------------------------------------------
# Test 3 — validate_upload raises 422 → storage never called
# ---------------------------------------------------------------------------

class TestUploadInvalidMimeReturns422:
    def test_upload_invalid_mime_returns_422(self):
        app = _make_test_app()
        mock_storage, mock_ocr, mock_redis = _make_mocks()

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch(
                "app.api.v1.documents.validate_upload",
                new=AsyncMock(
                    side_effect=HTTPException(
                        status_code=422,
                        detail="Detected MIME type 'text/plain' is not allowed.",
                    )
                ),
            ),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("doc.txt", b"hello", "text/plain")},
                data={"session_id": "test-session"},
            )

        assert resp.status_code == 422
        mock_storage.upload.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4 — Empty file bytes → 422 before storage
# ---------------------------------------------------------------------------

class TestUploadEmptyFileReturns422:
    def test_upload_empty_file_returns_422(self):
        app = _make_test_app()
        mock_storage, mock_ocr, mock_redis = _make_mocks()

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/v1/documents/upload",
                files={"file": ("photo.jpg", b"", "image/jpeg")},
                data={"session_id": "test-session"},
            )

        assert resp.status_code == 422
        mock_storage.upload.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — Storage upload raises → 500
# ---------------------------------------------------------------------------

class TestUploadStorageFailureReturns500:
    def test_upload_storage_failure_returns_500(self):
        app = _make_test_app()
        from app.services.storage_service import StorageError

        mock_storage, mock_ocr, mock_redis = _make_mocks(
            storage_upload_raises=StorageError("MinIO down")
        )

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = _upload_jpeg(client)

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Test 6 — Redis save failure does NOT fail the response
# ---------------------------------------------------------------------------

class TestUploadRedisSaveFailureDoesNotFailRequest:
    def test_upload_redis_save_failure_does_not_fail_request(self):
        app = _make_test_app()
        personal_data = _make_personal_data()
        mock_storage, mock_ocr, mock_redis = _make_mocks(
            ocr_decode_qr_result=personal_data,
            redis_save_raises=RuntimeError("Redis connection lost"),
        )

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = _upload_jpeg(client)

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


# ---------------------------------------------------------------------------
# Test 7 — Session stores extracted_personal_data + uploaded_document_path
# ---------------------------------------------------------------------------

class TestUploadSessionStoresExtractedPersonalData:
    def test_upload_session_stores_extracted_personal_data(self):
        app = _make_test_app()
        personal_data = _make_personal_data()
        mock_storage, mock_ocr, mock_redis = _make_mocks(
            ocr_decode_qr_result=personal_data,
        )

        saved: list[SessionData] = []

        async def _capture_save(session_id: str, session_data: SessionData) -> None:
            saved.append(session_data)

        mock_redis.save_session = _capture_save

        with (
            _bypass_rate_limit(),
            patch("app.api.v1.documents._get_storage", return_value=mock_storage),
            patch("app.api.v1.documents._get_ocr", return_value=mock_ocr),
            patch("app.api.v1.documents._get_redis", return_value=mock_redis),
            patch("app.api.v1.documents.validate_upload", new=AsyncMock(return_value=None)),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            _upload_jpeg(client)

        assert len(saved) == 1
        stored = saved[0]
        assert stored.extracted_personal_data is not None
        assert stored.extracted_personal_data.full_name == "Nguyễn Văn A"
        assert stored.uploaded_document_path is not None
        assert stored.uploaded_document_path.startswith("tmp/test-session/")


# ---------------------------------------------------------------------------
# Test 8 — _compute_ocr_confidence returns correct mean of field confidences
# ---------------------------------------------------------------------------

class TestOcrConfidenceMeanCalculation:
    def test_confidence_mean_from_field_confidences(self):
        from app.api.v1.documents import _compute_ocr_confidence

        pd = PersonalData(
            full_name="Test",
            id_number="001234567890",
            source_document_type="cccd",
            source_image_path="/tmp/img.jpg",
            extraction_confidence=0.0,  # should be ignored when field_confidences present
            field_confidences={"full_name": 0.9, "id_number": 0.5},
            extracted_at=datetime.utcnow(),
        )
        result = _compute_ocr_confidence(pd)
        assert abs(result - 0.7) < 1e-9  # mean(0.9, 0.5) == 0.7

    def test_confidence_falls_back_to_extraction_confidence_when_no_fields(self):
        from app.api.v1.documents import _compute_ocr_confidence

        pd = PersonalData(
            source_document_type="cccd",
            source_image_path="/tmp/img.jpg",
            extraction_confidence=0.42,
            field_confidences={},
            extracted_at=datetime.utcnow(),
        )
        result = _compute_ocr_confidence(pd)
        assert abs(result - 0.42) < 1e-9
