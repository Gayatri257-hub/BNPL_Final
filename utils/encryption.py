import hashlib
import os
from flask import current_app


def get_cipher():
    from cryptography.fernet import Fernet, InvalidToken  # noqa: F401
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in environment variables")
    if isinstance(key, str):
        key = key.encode()
    try:
        return Fernet(key)
    except Exception:
        raise ValueError(
            "ENCRYPTION_KEY is not a valid Fernet key. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )


def encrypt_field(value: str) -> str:
    if not value:
        return value
    try:
        cipher = get_cipher()
        return cipher.encrypt(value.encode()).decode()
    except Exception as e:
        current_app.logger.error(f"Encryption failed: {e}")
        raise


def decrypt_field(encrypted_value: str) -> str:
    if not encrypted_value:
        return encrypted_value
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_value.encode()).decode()
    except Exception:
        return '[decryption error]'


def hash_for_lookup(value: str) -> str:
    """SHA-256 hash used for database lookups without decrypting."""
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()

