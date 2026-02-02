"""Credential encryption utilities using Fernet symmetric encryption."""

import json
import os
from typing import Any

from cryptography.fernet import Fernet


class CredentialEncryption:
    """Handles encryption and decryption of sensitive credentials."""

    def __init__(self, encryption_key: str | None = None) -> None:
        """Initialize encryption with key from environment or provided key.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from
                           ENCRYPTION_KEY environment variable.
        """
        if encryption_key is None:
            encryption_key = os.getenv("ENCRYPTION_KEY")
            if encryption_key is None:
                raise ValueError("ENCRYPTION_KEY environment variable must be set or key provided")

        self._fernet = Fernet(encryption_key.encode())

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key as string.
        """
        return Fernet.generate_key().decode()

    def encrypt_credentials(self, credentials: dict[str, Any]) -> str:
        """Encrypt credentials dictionary to encrypted string.

        Args:
            credentials: Dictionary containing sensitive credential data.

        Returns:
            Encrypted credentials as base64-encoded string.
        """
        json_str = json.dumps(credentials)
        encrypted_bytes = self._fernet.encrypt(json_str.encode())
        return encrypted_bytes.decode()

    def decrypt_credentials(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt encrypted credentials string back to dictionary.

        Args:
            encrypted_data: Base64-encoded encrypted credentials string.

        Returns:
            Decrypted credentials dictionary.
        """
        decrypted_bytes = self._fernet.decrypt(encrypted_data.encode())
        return json.loads(decrypted_bytes.decode())


# Global instance - initialized when module is imported
_encryption: CredentialEncryption | None = None


def get_encryption() -> CredentialEncryption:
    """Get or create global encryption instance.

    Returns:
        Shared CredentialEncryption instance.
    """
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """Convenience function to encrypt credentials using global instance."""
    return get_encryption().encrypt_credentials(credentials)


def decrypt_credentials(encrypted_data: str) -> dict[str, Any]:
    """Convenience function to decrypt credentials using global instance."""
    return get_encryption().decrypt_credentials(encrypted_data)
