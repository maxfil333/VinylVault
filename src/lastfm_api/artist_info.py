import asyncio
from pprint import pprint

from src.config import cfg
from src.utils.utils import send_request_async


async def artist_info(artist_name: str, api_key: str = cfg.API_KEY) -> dict:
    params = {
        "method": "artist.getinfo",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }
    data = await send_request_async(params)
    if "error" in data:
        return data
    return data.get("artist", {})


async def artist_top_albums(artist_name: str, api_key: str = cfg.API_KEY, limit: int = 5) -> list[dict]:
    params = {
        "method": "artist.getTopAlbums",
        "artist": artist_name,
        "limit": limit,
        "api_key": api_key,
        "format": "json",
    }
    data = await send_request_async(params)
    return data.get("topalbums", {}).get("album", [])


if __name__ == "__main__":
    artist_name = "Brutus"
    artist_data = asyncio.run(artist_info(artist_name, cfg.API_KEY))

    if "error" in artist_data:
        print(f"Ошибка: {artist_data['error']}")
    else:
        print(f"Имя: {artist_data.get('name')}")
        print(f"Слушателей: {artist_data.get('stats', {}).get('listeners')}")
        print(f"Теги: {', '.join(tag['name'] for tag in artist_data.get('tags', {}).get('tag', []))}")
        print(f"Биография: {artist_data.get('bio', {}).get('summary')}")

    print("=" * 50)

    top_albums = asyncio.run(artist_top_albums(artist_name, cfg.API_KEY))
    pprint(top_albums)
