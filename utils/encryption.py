import hashlib
import os
from cryptography.fernet import Fernet
from flask import current_app


def get_cipher():
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in config")
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_field(value: str) -> str:
    if not value:
        return value
    cipher = get_cipher()
    return cipher.encrypt(value.encode()).decode()


def decrypt_field(encrypted_value: str) -> str:
    if not encrypted_value:
        return encrypted_value
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_value.encode()).decode()
    except Exception:
        return '[decryption error]'


def hash_for_lookup(value: str) -> str:
    """SHA-256 hash used for database lookups (e.g. email search) without decrypting."""
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()
