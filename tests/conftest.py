"""Pytest configuration: set required env vars before any test module imports.

`arguslm.server.main` instantiates `Settings()` at import time (via the db
package), and `Settings` validates `ENCRYPTION_KEY` / `SECRET_KEY` are non-empty.
Per-test fixtures run *after* collection, which is too late — the env must be
populated before pytest imports any `tests/test_*.py` module.
"""

import os

from arguslm.server.core.security import CredentialEncryption

os.environ.setdefault("ENCRYPTION_KEY", CredentialEncryption.generate_key())
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
