"""Unit test configuration.

Registers stub modules for heavy native dependencies so that:
  - python-magic (libmagic DLL) is never loaded during unit tests.
  - Tests that need specific MIME results patch magic.from_buffer directly
    via unittest.mock.patch("magic.from_buffer", return_value="...").
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub out python-magic before any test module imports it.
# Without this, importing app.core.file_validator on Windows triggers an
# access violation inside the libmagic DLL during pytest collection.
# ---------------------------------------------------------------------------
if "magic" not in sys.modules:
    _magic_stub = MagicMock()
    _magic_stub.from_buffer = MagicMock(return_value="application/octet-stream")
    sys.modules["magic"] = _magic_stub

# ---------------------------------------------------------------------------
# Stub out pyzbar before any test module imports it.
# pyzbar requires the libzbar0 native library which may not be installed in CI
# or on developer machines that haven't run the project setup script yet.
# Tests that need specific pyzbar results patch app.services.ocr_service.pyzbar_decode
# directly via unittest.mock.patch.
# ---------------------------------------------------------------------------
if "pyzbar" not in sys.modules:
    _pyzbar_stub = MagicMock()
    _pyzbar_stub.decode = MagicMock(return_value=[])
    sys.modules["pyzbar"] = _pyzbar_stub
    sys.modules["pyzbar.pyzbar"] = _pyzbar_stub


# ---------------------------------------------------------------------------
# Reusable image fixture — a committed JPEG that cv2.imread() can always read.
# Use this instead of tmp_path alone whenever a test calls cv2.imread() or
# passes an image path to decode_qr() / _preprocess_for_ocr().
# ---------------------------------------------------------------------------
@pytest.fixture
def minimal_image_path() -> str:
    """Return path to tests/fixtures/minimal_cccd.jpg — a real 200×120 JPEG."""
    return str(Path(__file__).parent.parent / "fixtures" / "minimal_cccd.jpg")
