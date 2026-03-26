"""Unit test configuration.

Registers stub modules for heavy native dependencies so that:
  - python-magic (libmagic DLL) is never loaded during unit tests.
  - Tests that need specific MIME results patch magic.from_buffer directly
    via unittest.mock.patch("magic.from_buffer", return_value="...").
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out python-magic before any test module imports it.
# Without this, importing app.core.file_validator on Windows triggers an
# access violation inside the libmagic DLL during pytest collection.
# ---------------------------------------------------------------------------
if "magic" not in sys.modules:
    _magic_stub = MagicMock()
    _magic_stub.from_buffer = MagicMock(return_value="application/octet-stream")
    sys.modules["magic"] = _magic_stub
