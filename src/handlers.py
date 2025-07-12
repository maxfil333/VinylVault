from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pages import generate_user_page


class PageNotFoundHandler(BaseHTTPMiddleware):

    def __init__(self, app, vinyl_vault_users: AsyncIOMotorCollection):
        super().__init__(app)
        self.vinyl_vault_users = vinyl_vault_users  # Сохраняем коллекцию в middleware

    async def dispatch(self, request, call_next):
        response = await call_next(request)  # Отправляем запрос в FastAPI

        # Если сервер вернул 404 и путь ведёт к странице пользователя
        if response.status_code == 404 and request.url.path.startswith("/static/data/users/"):
            _id = request.url.path.split("/")[-1].replace(".html", "")
            user = await self.vinyl_vault_users.find_one({"user_id": _id})

            # Генерируем страницу
            await generate_user_page(user_id=_id, username=user.get("username"))

            # Повторный редирект, теперь файл уже существует
            return RedirectResponse(url=f"/static/data/users/{_id}.html", status_code=303)

        return response  # Отдаём ответ клиенту


from fastapi import Request, status, FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def global_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=303)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})