import requests

from src.config import API_KEY


def get_artist_info(artist_name, api_key):
    """
    Получить информацию об артисте из Last.fm API.

    :param artist_name: Имя артиста (str)
    :param api_key: API ключ Last.fm (str)
    :return: Словарь с информацией об артисте или сообщение об ошибке.
    """
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.getinfo",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Вызывает исключение для статусов ошибок HTTP

        data = response.json()
        if "error" in data:
            return {"error": data["message"]}

        artist_info = data.get("artist", {})
        return artist_info

    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка запроса: {str(e)}"}


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
