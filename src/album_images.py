import os
import requests
from urllib.parse import urlparse

from src.config import API_KEY


def get_artist_albums(artist_name, api_key):
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
        return [{"name": album["name"], "image": album["image"][-1]["#text"]} for album in albums if
                album["image"][-1]["#text"]]

    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка запроса: {str(e)}"}


def download_images(album_list, output_dir):
    """
    Скачивает изображения альбомов в указанную директорию.

    :param album_list: Список альбомов с обложками (list)
    :param output_dir: Директория для сохранения изображений (str)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for album in album_list:
        image_url = album["image"]
        if not image_url:
            continue

        try:
            # Определяем имя файла
            file_name = os.path.join(output_dir, os.path.basename(urlparse(image_url).path))
            # Скачиваем изображение
            response = requests.get(image_url, stream=True)
            response.raise_for_status()

            with open(file_name, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Скачано: {file_name}")

        except requests.exceptions.RequestException as e:
            print(f"Ошибка скачивания {image_url}: {str(e)}")


if __name__ == "__main__":
    artist_name = "Brutus"
    output_dir = "../album_covers"

    albums = get_artist_albums(artist_name, API_KEY)
    if "error" in albums:
        print(f"Ошибка: {albums['error']}")
    else:
        download_images(albums, output_dir)
