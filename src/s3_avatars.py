"""Загрузка аватаров в Selectel S3; раздача по публичному CDN-домену (s3_base_domain)."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from src.config import cfg

DEFAULT_AVATAR_KEY = "avatars/default_avatar.jpg"
USER_AVATAR_PREFIX = "user_avatars"
_USER_AVATAR_EXTS = (".jpg", ".png", ".webp", ".gif")

# Расширение файла (нижний регистр) → Content-Type для S3
AVATAR_EXT_TO_CONTENT_TYPE: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

LEGACY_STATIC_DEFAULT_AVATAR = "/static/data/avatars/default_avatar.jpg"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
    )


def _public_base() -> str:
    return cfg.s3_base_domain.rstrip("/")


def public_url_for_key(key: str) -> str:
    return f"{_public_base()}/{key.lstrip('/')}"


def default_avatar_public_url() -> str:
    return public_url_for_key(DEFAULT_AVATAR_KEY)


def coalesce_avatar_url(stored: str | None) -> str:
    """None или устаревший путь к дефолту на диске → публичный URL дефолта в CDN."""
    if not stored:
        return default_avatar_public_url()
    s = stored.strip()
    if s == LEGACY_STATIC_DEFAULT_AVATAR:
        return default_avatar_public_url()
    return s


def _delete_user_avatar_variants(user_id: str) -> None:
    client = _s3_client()
    for ext in _USER_AVATAR_EXTS:
        key = f"{USER_AVATAR_PREFIX}/{user_id}{ext}"
        try:
            client.delete_object(Bucket=cfg.s3_bucket, Key=key)
        except ClientError:
            pass


def upload_user_avatar_to_s3(user_id: str, file_bytes: bytes, content_type: str, ext: str) -> str:
    """Удаляет прежние объекты аватара пользователя, загружает новый, возвращает публичный URL."""
    _delete_user_avatar_variants(user_id)
    key = f"{USER_AVATAR_PREFIX}/{user_id}{ext}"
    client = _s3_client()
    client.put_object(
        Bucket=cfg.s3_bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
        ACL="public-read",
    )
    return public_url_for_key(key)


def upload_public_bytes(key: str, file_bytes: bytes, content_type: str) -> str:
    """Публичный объект (например дефолтный аватар). Возвращает URL."""
    client = _s3_client()
    client.put_object(
        Bucket=cfg.s3_bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
        ACL="public-read",
    )
    return public_url_for_key(key)
