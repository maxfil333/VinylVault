import asyncio
from pprint import pprint

from src.config import cfg
from src.utils.utils import send_request_async


async def album_getinfo(artist_name: str, album_name: str, api_key: str = cfg.API_KEY) -> dict:
    """
    Get album by album_name and artist_name.
    :return: Словарь с информацией об альбоме или {"error": "..."}.
    """
    params = {
        "method": "album.getInfo",
        "artist": artist_name,
        "album": album_name,
        "api_key": api_key,
        "format": "json",
    }
    return await send_request_async(params)


async def album_search(album_name: str, api_key: str = cfg.API_KEY, limit: int = 5) -> list[dict]:
    """Get albums list by album_name."""
    params = {
        "method": "album.search",
        "album": album_name,
        "api_key": api_key,
        "limit": limit,
        "format": "json",
    }
    data = await send_request_async(params)
    return data.get("results", {}).get("albummatches", {}).get("album", [])


if __name__ == "__main__":
    artist_name = "Brutus"
    album_name = "Unison life"

    album_data = asyncio.run(album_getinfo(artist_name, album_name, cfg.API_KEY))
    pprint(album_data)

    print("-" * 70)

    album_search_data = asyncio.run(album_search(album_name, cfg.API_KEY, limit=5))
    pprint(album_search_data)
