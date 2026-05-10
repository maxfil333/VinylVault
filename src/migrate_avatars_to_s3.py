"""Дефолтный аватар (other/), локальные user_avatars → avatars/, правка legacy URL в MongoDB.

Запуск: python -m src.migrate_avatars_to_s3
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from src.config import cfg
from src.database import close_database, init_database, vinyl_vault_users
from src.s3_avatars import (
    AVATAR_EXT_TO_CONTENT_TYPE,
    DEFAULT_AVATAR_KEY,
    LEGACY_STATIC_DEFAULT_AVATARS,
    default_avatar_public_url,
    normalize_stored_avatar_url,
    upload_public_bytes,
    upload_user_avatar_to_s3,
)

USER_AVATARS_DIR: Path = cfg.WEBSITE_DIR / "data" / "user_avatars"
_LEGACY_STATIC_USER = re.compile(r"^/static/data/user_avatars/(.+)$")


def _default_avatar_local_path() -> Path | None:
    other_p = cfg.WEBSITE_DIR / "data" / "other" / "default_avatar.jpg"
    if other_p.is_file():
        return other_p
    legacy = cfg.WEBSITE_DIR / "data" / "avatars" / "default_avatar.jpg"
    if legacy.is_file():
        return legacy
    return None


async def _migrate_default() -> None:
    path = _default_avatar_local_path()
    if not path:
        print("[skip] нет default_avatar.jpg в data/other/ или data/avatars/")
        return
    url = await upload_public_bytes(
        DEFAULT_AVATAR_KEY,
        path.read_bytes(),
        "image/jpeg",
    )
    print(f"[ok] дефолтный аватар в S3 ({path.relative_to(cfg.WEBSITE_DIR)}): {url}")


async def _migrate_local_files(coll) -> None:
    if not USER_AVATARS_DIR.is_dir():
        print(f"[skip] нет каталога {USER_AVATARS_DIR}")
        return
    for path in sorted(USER_AVATARS_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        ext = path.suffix.lower()
        if ext not in AVATAR_EXT_TO_CONTENT_TYPE:
            print(f"[skip] неизвестное расширение: {path.name}")
            continue
        user_id = path.stem
        data = path.read_bytes()
        content_type = AVATAR_EXT_TO_CONTENT_TYPE[ext]
        url = await upload_user_avatar_to_s3(user_id, data, content_type, ext)
        result = await coll.update_one({"user_id": user_id}, {"$set": {"avatar_url": url}})
        print(f"[ok] {path.name} -> {url} (matched={result.matched_count})")


async def _migrate_legacy_db_urls(coll) -> None:
    cursor = coll.find({"avatar_url": {"$regex": r"^/static/data/user_avatars/"}})
    async for doc in cursor:
        owner_id = doc.get("user_id")
        raw = (doc.get("avatar_url") or "").strip()
        m = _LEGACY_STATIC_USER.match(raw)
        if not m:
            continue
        fname = m.group(1)
        local = USER_AVATARS_DIR / fname
        if not local.is_file():
            new_url = default_avatar_public_url()
            await coll.update_one({"user_id": owner_id}, {"$set": {"avatar_url": new_url}})
            print(f"[warn] {owner_id}: файла нет ({fname}), в БД -> дефолт CDN")
            continue
        ext = local.suffix.lower()
        content_type = AVATAR_EXT_TO_CONTENT_TYPE.get(ext)
        if not content_type:
            new_url = default_avatar_public_url()
            await coll.update_one({"user_id": owner_id}, {"$set": {"avatar_url": new_url}})
            print(f"[warn] {owner_id}: плохое расширение {fname}, в БД -> дефолт CDN")
            continue
        data = local.read_bytes()
        url = await upload_user_avatar_to_s3(owner_id, data, content_type, ext)
        await coll.update_one({"user_id": owner_id}, {"$set": {"avatar_url": url}})
        print(f"[ok] legacy /static/... пользователя {owner_id} -> {url}")


async def _normalize_static_defaults_in_db(coll) -> None:
    for legacy in LEGACY_STATIC_DEFAULT_AVATARS:
        result = await coll.update_many(
            {"avatar_url": legacy},
            {"$set": {"avatar_url": default_avatar_public_url()}},
        )
        if result.modified_count:
            print(f"[ok] заменён {legacy!r} в БД: {result.modified_count} док.")


async def _rewrite_cdn_avatar_urls_in_db(coll) -> None:
    """Переписать в Mongo старые https URL: /data/, user_avatars/, avatars/default_avatar.jpg."""
    cursor = coll.find({"avatar_url": {"$regex": "^https?://"}})
    async for doc in cursor:
        raw = (doc.get("avatar_url") or "").strip()
        if not raw:
            continue
        final = normalize_stored_avatar_url(raw)
        if final != raw:
            await coll.update_one({"user_id": doc["user_id"]}, {"$set": {"avatar_url": final}})
            print(f"[ok] CDN URL пользователя {doc.get('user_id')}: обновлён")


async def main() -> None:
    await init_database()
    try:
        coll = await vinyl_vault_users()
        await _migrate_default()
        await _migrate_local_files(coll)
        await _migrate_legacy_db_urls(coll)
        await _normalize_static_defaults_in_db(coll)
        await _rewrite_cdn_avatar_urls_in_db(coll)
        print("Готово.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
