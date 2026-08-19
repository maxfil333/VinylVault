"""Хэширование и проверка паролей (bcrypt)."""

from __future__ import annotations

import hashlib

import bcrypt


def _password_digest(plain: str) -> bytes:
    """SHA-256 перед bcrypt: bcrypt принимает максимум 72 байта, digest всегда 32."""
    return hashlib.sha256(plain.encode("utf-8")).digest()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_password_digest(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        hashed_bytes = hashed.encode("utf-8")
        if bcrypt.checkpw(_password_digest(plain), hashed_bytes):
            return True
        # Старые записи: bcrypt от plain-текста без pre-hash
        return bcrypt.checkpw(plain.encode("utf-8"), hashed_bytes)
    except (ValueError, TypeError):
        return False
