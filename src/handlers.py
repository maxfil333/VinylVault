from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from pymongo.collection import Collection

from src.pages import generate_user_page


class PageNotFoundHandler(BaseHTTPMiddleware):

    def __init__(self, app, vinyl_vault_users: Collection):
        super().__init__(app)
        self.vinyl_vault_users = vinyl_vault_users  # Сохраняем коллекцию в middleware

    async def dispatch(self, request, call_next):
        response = await call_next(request)  # Отправляем запрос в FastAPI

        # Если сервер вернул 404 и путь ведёт к странице пользователя
        if response.status_code == 404 and request.url.path.startswith("/user/"):
            _id = request.url.path.split("/")[-1].replace(".html", "")
            user = self.vinyl_vault_users.find_one({"_id": _id})

            # Генерируем страницу
            await generate_user_page(user_id=_id, username=user.get("username"))

            # Повторный редирект, теперь файл уже существует
            return RedirectResponse(url=f"/user/{_id}.html", status_code=303)

        return response  # Отдаём ответ клиенту
