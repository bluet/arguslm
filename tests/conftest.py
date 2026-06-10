"""Pytest configuration: set required env vars before any test module imports.

`arguslm.server.main` instantiates `Settings()` at import time (via the db
package), and `Settings` validates `ENCRYPTION_KEY` / `SECRET_KEY` are non-empty.
Per-test fixtures run *after* collection, which is too late — the env must be
populated before pytest imports any `tests/test_*.py` module.
"""

import base64
import os

try:
    from arguslm.server.core.security import CredentialEncryption

    _encryption_key = CredentialEncryption.generate_key()
except ImportError:
    # Server deps (cryptography) not installed — generate a valid Fernet-format key
    # using stdlib only so the core/SDK tests can still be collected and run.
    _encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode()

os.environ.setdefault("ENCRYPTION_KEY", _encryption_key)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
