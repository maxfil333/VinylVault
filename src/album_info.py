from src.config import API_KEY
from utils import send_request


def get_album_info(artist_name: str, album_name: str, api_key: str) -> dict:
    """
    Get album by album_name and artist_name
    :param artist_name: Имя артиста
    :param album_name: Имя альбома
    :param api_key: API ключ Last.fm
    :return: Словарь с информацией об альбоме или сообщением об ошибке.
    """
    params = {
        "method": "album.getInfo",
        "artist": artist_name,
        "album": album_name,
        "api_key": api_key,
        "format": "json",
    }
    return send_request(params)


def album_search(album_name: str, api_key: str, limit=5) -> list:
    """
    Get albums list by album_name
    :param album_name: Имя альбома
    :param api_key: API ключ Last.fm
    :param limit: Количество результатов
    :return: Словарь с информацией об альбоме или сообщением об ошибке.
    """

    params = {
        "method": "album.search",
        "album": album_name,
        "api_key": api_key,
        "limit": limit,
        "format": "json",
    }
    return send_request(params).get('results', {}).get('albummatches', {}).get('album', [])


if __name__ == '__main__':
    artist_name = "brutus"
    album_name = "Unison life"

    album_data = get_album_info(artist_name, album_name, API_KEY)
    print(album_data)

    print('-'*30)

    album_search_data = album_search(album_name, API_KEY, limit=5)
    for alb in album_search_data:
        print(alb)
