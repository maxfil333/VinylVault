"""Полная перезаливка CDN: avatars + backgrounds + other, затем дефолт/пользовательские аватары и правка MongoDB.

    python -m src.reupload_all_cdn
"""

from __future__ import annotations

import asyncio

from src.migrate_avatars_to_s3 import main as migrate_avatars_main
from src.migrate_website_data_to_s3 import main as migrate_data_main


async def main() -> None:
    await migrate_data_main()
    await migrate_avatars_main()


if __name__ == "__main__":
    asyncio.run(main())
