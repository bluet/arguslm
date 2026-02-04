#!/usr/bin/env python3
"""Generate secure secrets for ArgusLM.

Usage:
    python scripts/generate-secrets.py > .env
    # Or append to existing:
    python scripts/generate-secrets.py >> .env

Requirements:
    pip install cryptography
    # Or run via Docker (no local dependencies):
    docker run --rm python:3.11-slim sh -c "pip install -q cryptography && python -c '
from cryptography.fernet import Fernet
import secrets
print(f\"ENCRYPTION_KEY={Fernet.generate_key().decode()}\")
print(f\"SECRET_KEY={secrets.token_urlsafe(32)}\")
print(f\"DB_PASSWORD={secrets.token_urlsafe(24)}\")
'"
"""

import secrets

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("Error: cryptography package not installed.")
    print("Install with: pip install cryptography")
    print("Or use Docker (see docstring above)")
    exit(1)

print("# Generated secrets for ArgusLM")
print("# Add these to your .env file")
print()
print(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
print(f"SECRET_KEY={secrets.token_urlsafe(32)}")
print(f"DB_PASSWORD={secrets.token_urlsafe(24)}")
