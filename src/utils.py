import requests

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
