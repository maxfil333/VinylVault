import requests
import os

from src.config import URL


def send_request(params: dict) -> dict:
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status()  # Вызывает исключение для статусов ошибок HTTP
        data = response.json()
        if "error" in data:
            return {"error": data["message"]}
        return data

    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка запроса: {str(e)}"}


def load_html(filename: str, filedir: str) -> str:
    """Считывает содержимое HTML-файла из директории website."""
    file_path = os.path.join(filedir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
