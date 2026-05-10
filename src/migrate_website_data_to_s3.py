"""Загрузка содержимого website/data/ в S3 (префикс ключей data/...).

Не переносится (осознанно):
  - data/users/ — генерируемые HTML страницы профиля, сессии, пересборка на /me;
  - data/user_avatars/ — пользовательские аватары уже в S3 (префикс user_avatars/);
  - data/avatars/default_avatar.jpg — тот же файл, что avatars/default_avatar.jpg в migrate_avatars_to_s3.

Запуск: python -m src.migrate_website_data_to_s3
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.config import cfg
from src.data_cdn import upload_data_file

DATA_ROOT: Path = cfg.WEBSITE_DIR / "data"
# Каталоги не заливаем как объекты; users — HTML на сервере; user_avatars — отдельная схема S3.
SKIP_TOP_LEVEL_DIRS = frozenset({"users", "user_avatars"})
# Дубликат дефолтного аватара (уже под ключом avatars/default_avatar.jpg).
_DEFAULT_AVATAR_DUP = "avatars/default_avatar.jpg"


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
        rel_posix = rel.as_posix()
        if rel_posix.replace("\\", "/") == _DEFAULT_AVATAR_DUP:
            print(f"[skip] дубликат дефолтного аватара: {rel_posix}")
            continue
        url = await asyncio.to_thread(upload_data_file, path, rel_posix)
        print(f"[ok] {rel_posix} -> {url}")

    print("Готово (data/* в S3, кроме users/ и user_avatars/).")


if __name__ == "__main__":
    asyncio.run(main())
