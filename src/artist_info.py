from pprint import pprint

from src.config import API_KEY
from src.utils import send_request


def artist_info(artist_name: str, api_key: str) -> dict:
    params = {
        "method": "artist.getinfo",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }
    return send_request(params).get("artist", {})


def artist_top_albums(artist_name: str, api_key: str, limit: int = 5) -> dict:
    params = {
        "method": "artist.getTopAlbums",
        "artist": artist_name,
        "limit": limit,
        "api_key": api_key,
        "format": "json",
    }
    return send_request(params).get("topalbums", {}).get('album')


if __name__ == "__main__":
    artist_name = "Brutus"
    artist_data = artist_info(artist_name, API_KEY)

    if "error" in artist_data:
        print(f"Ошибка: {artist_data['error']}")
    else:
        print(f"Имя: {artist_data.get('name')}")
        print(f"Слушателей: {artist_data.get('stats', {}).get('listeners')}")
        print(f"Теги: {', '.join(tag['name'] for tag in artist_data.get('tags', {}).get('tag', []))}")
        print(f"Биография: {artist_data.get('bio', {}).get('summary')}")

    print('=' * 50)

    top_albums = artist_top_albums(artist_name, API_KEY)
    pprint(top_albums)
