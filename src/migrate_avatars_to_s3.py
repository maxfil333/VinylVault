"""Миграция локальных аватаров в S3 и обновление ссылок в MongoDB.

Запуск из корня проекта (с активированным .venv):

    python -m src.migrate_avatars_to_s3

Шаги: дефолтный аватар → файлы в website/data/user_avatars/ → документы с legacy URL в БД.
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
    LEGACY_STATIC_DEFAULT_AVATAR,
    default_avatar_public_url,
    upload_public_bytes,
    upload_user_avatar_to_s3,
)

USER_AVATARS_DIR: Path = cfg.WEBSITE_DIR / "data" / "user_avatars"
_LEGACY_USER_AVATAR_RE = re.compile(r"^/static/data/user_avatars/(.+)$")


async def _migrate_default() -> None:
    path = cfg.WEBSITE_DIR / "data" / "avatars" / "default_avatar.jpg"
    if not path.is_file():
        print(f"[skip] нет файла дефолтного аватара: {path}")
        return
    url = await asyncio.to_thread(
        upload_public_bytes,
        DEFAULT_AVATAR_KEY,
        path.read_bytes(),
        "image/jpeg",
    )
    print(f"[ok] дефолтный аватар в S3: {url}")


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
        url = await asyncio.to_thread(
            upload_user_avatar_to_s3,
            user_id,
            data,
            content_type,
            ext,
        )
        result = await coll.update_one({"user_id": user_id}, {"$set": {"avatar_url": url}})
        print(f"[ok] {path.name} -> {url} (matched={result.matched_count})")


async def _migrate_legacy_db_urls(coll) -> None:
    cursor = coll.find({"avatar_url": {"$regex": r"^/static/data/user_avatars/"}})
    async for doc in cursor:
        owner_id = doc.get("user_id")
        raw = (doc.get("avatar_url") or "").strip()
        m = _LEGACY_USER_AVATAR_RE.match(raw)
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
        url = await asyncio.to_thread(
            upload_user_avatar_to_s3,
            owner_id,
            data,
            content_type,
            ext,
        )
        await coll.update_one({"user_id": owner_id}, {"$set": {"avatar_url": url}})
        print(f"[ok] legacy URL пользователя {owner_id} -> {url}")


async def _normalize_static_default_in_db(coll) -> None:
    result = await coll.update_many(
        {"avatar_url": LEGACY_STATIC_DEFAULT_AVATAR},
        {"$set": {"avatar_url": default_avatar_public_url()}},
    )
    if result.modified_count:
        print(f"[ok] заменён устаревший дефолт /static/... в БД: {result.modified_count} док.")


async def main() -> None:
    await init_database()
    try:
        coll = await vinyl_vault_users()
        await _migrate_default()
        await _migrate_local_files(coll)
        await _migrate_legacy_db_urls(coll)
        await _normalize_static_default_in_db(coll)
        print("Готово.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
