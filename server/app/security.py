from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    """Derive a deterministic 32-byte URL-safe Fernet key from the configured secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().secret_key.encode()).digest())
    return Fernet(key)


def encrypt_token(plaintext: str | None) -> str | None:
    """Encrypt a sensitive token for storage at rest. Returns None/empty unchanged."""
    if not plaintext:
        return plaintext
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str | None) -> str | None:
    """Decrypt a token stored with :func:`encrypt_token`.

    Falls back to returning the input unchanged if it isn't valid ciphertext — this keeps
    values written before encryption was enabled working during migration.
    """
    if not ciphertext:
        return ciphertext
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return ciphertext
