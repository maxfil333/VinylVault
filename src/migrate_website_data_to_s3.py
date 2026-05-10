"""Загрузка website/data/{avatars,backgrounds,other} в S3 (те же ключи: avatars/..., backgrounds/..., other/...).

Не заливается: users/, user_avatars/ (HTML и пользовательские аватары — отдельно).
Не заливается файл avatars/default_avatar.jpg с диска — канонический дефолт в other/default_avatar.jpg.

Запуск: python -m src.migrate_website_data_to_s3
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.config import cfg
from src.data_cdn import upload_data_file

DATA_ROOT: Path = cfg.WEBSITE_DIR / "data"
ONLY_TOP = frozenset({"avatars", "backgrounds", "other"})
SKIP_TOP_LEVEL_DIRS = frozenset({"users", "user_avatars"})
# Старый путь дефолта на диске — не дублировать в S3 под avatars/
_SKIP_DISK_DEFAULT_IN_AVATARS = "avatars/default_avatar.jpg"


async def main() -> None:
    if not DATA_ROOT.is_dir():
        print(f"Нет каталога {DATA_ROOT}")
        return

    for path in sorted(DATA_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DATA_ROOT)
        if rel.parts and rel.parts[0] in SKIP_TOP_LEVEL_DIRS:
            continue
        if rel.parts and rel.parts[0] not in ONLY_TOP:
            continue
        rel_posix = rel.as_posix().replace("\\", "/")
        if rel_posix == _SKIP_DISK_DEFAULT_IN_AVATARS:
            print(f"[skip] дефолт только из other/default_avatar.jpg: {rel_posix}")
            continue
        url = await asyncio.to_thread(upload_data_file, path, rel_posix)
        print(f"[ok] {rel_posix} -> {url}")

    print("Готово (avatars, backgrounds, other → S3).")


if __name__ == "__main__":
    asyncio.run(main())
