import os
import requests
from urllib.parse import urlparse

from src.config import API_KEY


def get_artist_albums(artist_name, api_key) -> dict:
    """
    Получить список альбомов артиста с обложками.

    :param artist_name: Имя артиста (str)
    :param api_key: API ключ Last.fm (str)
    :return: Список альбомов с обложками.
    """
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.gettopalbums",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
        "limit": 5  # Максимум альбомов
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {"error": data["message"]}

        albums = data.get("topalbums", {}).get("album", [])

        result = []
        for album in albums:
            result.append({'album_name': album["name"],
                           'image_link_main': album["image"][-1]["#text"],
                           'image_link_reserve': album["image"][-2]["#text"]})
        return {"result": result}

    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка запроса: {str(e)}"}


def download_by_link(link: str, output_dir: str) -> None:
    response = requests.get(link, stream=True)
    response.raise_for_status()
    file_name = os.path.join(output_dir, os.path.basename(urlparse(link).path))
    with open(file_name, "wb") as file:
        for chunk in response.iter_content(1024):
            file.write(chunk)
    print(f"Скачано: {file_name}")


def download_images(albums, output_dir) -> None:
    """
    Скачивает изображения альбомов в указанную директорию.

    :param albums: {'result': `Список альбомов с обложками (list)`}
    :param output_dir: Директория для сохранения изображений (str)
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for album in albums['result']:
        image_link_main = album["image_link_main"]
        image_link_reserve = album["image_link_reserve"]

        try:
            download_by_link(image_link_main, output_dir)
        except requests.exceptions.RequestException as e:
            print(f"Ошибка скачивания {image_link_main}: {str(e)}")
            print(f"Попытка скачивания резервного изображения...")
            try:
                download_by_link(image_link_reserve, output_dir)
            except requests.exceptions.RequestException as e:
                print(f"Ошибка скачивания резервного изображения {image_link_main}: {str(e)}")


if __name__ == "__main__":
    artist_name = "Brutus"
    output_dir = "../album_covers"

    albums = get_artist_albums(artist_name, API_KEY)
    if "error" in albums:
        print(f"Ошибка: {albums['error']}")
    else:
        download_images(albums, output_dir)
