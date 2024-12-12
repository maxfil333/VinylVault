from src.config import API_KEY
from src.utils import send_request


def get_artist_info(artist_name: str, api_key: str) -> dict:
    """
    Получить информацию об артисте из Last.fm API.
    :param artist_name: Имя артиста (str)
    :param api_key: API ключ Last.fm (str)
    :return: Словарь с информацией об артисте или сообщением об ошибке.
    """
    params = {
        "method": "artist.getinfo",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }
    return send_request(params).get("artist", {})


if __name__ == "__main__":
    artist_name = "Brutus"
    artist_data = get_artist_info(artist_name, API_KEY)

    if "error" in artist_data:
        print(f"Ошибка: {artist_data['error']}")
    else:
        print(f"Имя: {artist_data.get('name')}")
        print(f"Слушателей: {artist_data.get('stats', {}).get('listeners')}")
        print(f"Теги: {', '.join(tag['name'] for tag in artist_data.get('tags', {}).get('tag', []))}")
        print(f"Биография: {artist_data.get('bio', {}).get('summary')}")
