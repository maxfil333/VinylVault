"""Аватары в Selectel S3: дефолт в other/, загрузки пользователей в avatars/{user_id}.ext."""

from __future__ import annotations

import re
from typing import Any

from botocore.exceptions import ClientError

from src.config import cfg
from src.s3_async import s3_client

# Ключи в бакете (корень CDN = s3_base_domain)
DEFAULT_AVATAR_KEY = "other/default_avatar.jpg"
USER_AVATAR_PREFIX = "avatars"
_USER_AVATAR_EXTS = (".jpg", ".png", ".webp", ".gif")

AVATAR_EXT_TO_CONTENT_TYPE: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

LEGACY_STATIC_DEFAULT_AVATARS = frozenset(
    {
        "/static/data/avatars/default_avatar.jpg",
        "/static/data/other/default_avatar.jpg",
    }
)
_LEGACY_STATIC_USER_AVATAR = re.compile(r"^/static/data/user_avatars/(.+)$")


def _public_base() -> str:
    return cfg.s3_base_domain.rstrip("/")


def public_url_for_key(key: str) -> str:
    return f"{_public_base()}/{key.lstrip('/')}"


def default_avatar_public_url() -> str:
    return public_url_for_key(DEFAULT_AVATAR_KEY)


def normalize_stored_avatar_url(stored: str) -> str:
    """Старые CDN-пути: .../data/... → без data/; user_avatars → avatars; старый дефолт avatars/default_avatar.jpg → other/."""
    s = stored.strip()
    base = _public_base()
    data_seg = f"{base}/data/"
    if s.startswith("http") and data_seg in s:
        s = s.replace(data_seg, f"{base}/")
    if "/user_avatars/" in s:
        s = s.replace("/user_avatars/", "/avatars/")
    if s.startswith("http") and (
        s.rstrip("/").endswith("/avatars/default_avatar.jpg")
        or "/avatars/default_avatar.jpg?" in s
    ):
        return default_avatar_public_url()
    return s


def coalesce_avatar_url(stored: str | None) -> str:
    """None, устаревшие /static/... и нормализация старых CDN-URL."""
    if not stored:
        return default_avatar_public_url()
    s = stored.strip()
    if s in LEGACY_STATIC_DEFAULT_AVATARS:
        return default_avatar_public_url()
    if s.startswith("http://") or s.startswith("https://"):
        return normalize_stored_avatar_url(s)
    m = _LEGACY_STATIC_USER_AVATAR.match(s)
    if m:
        return public_url_for_key(f"{USER_AVATAR_PREFIX}/{m.group(1)}")
    return s


async def _delete_user_avatar_variants(client: Any, user_id: str) -> None:
    for ext in _USER_AVATAR_EXTS:
        key = f"{USER_AVATAR_PREFIX}/{user_id}{ext}"
        try:
            await client.delete_object(Bucket=cfg.s3_bucket, Key=key)
        except ClientError:
            pass


async def upload_user_avatar_to_s3(user_id: str, file_bytes: bytes, content_type: str, ext: str) -> str:
    """Удаляет прежние объекты аватара пользователя, загружает новый, возвращает публичный URL."""
    key = f"{USER_AVATAR_PREFIX}/{user_id}{ext}"
    async with s3_client() as client:
        await _delete_user_avatar_variants(client, user_id)
        await client.put_object(
            Bucket=cfg.s3_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            ACL="public-read",
        )
    return public_url_for_key(key)


async def upload_public_bytes(key: str, file_bytes: bytes, content_type: str) -> str:
    async with s3_client() as client:
        await client.put_object(
            Bucket=cfg.s3_bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            ACL="public-read",
        )
    return public_url_for_key(key)
