from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse

from src.pages import generate_user_page
from src.s3_avatars import coalesce_avatar_url


class PageNotFoundHandler(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # --- Ранние выходы, чтобы не городить вложенности ---
        if response.status_code != 404:
            return response

        path = request.url.path
        if not path.startswith("/static/data/users/"):
            return response

        # --- Попытка получить коллекцию ---
        app_state = getattr(request.app, "state", None)
        users_collection = getattr(app_state, "users_collection", None)

        if users_collection is None:
            return response

        # --- Извлекаем user_id ---
        _id = path.rsplit("/", 1)[-1].replace(".html", "")
        user = await users_collection.find_one({"user_id": _id})

        if not user:
            return response  # Пользователь реально отсутствует → обычный 404

        # --- Генерация HTML ---
        await generate_user_page(
            user_id=_id,
            username=user.get("username"),
            avatar_url=coalesce_avatar_url(user.get("avatar_url")),
        )

        # --- Редирект на готовую страницу ---
        return RedirectResponse(
            url=f"/static/data/users/{_id}.html",
            status_code=303
        )


from fastapi import Request, status, FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def global_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login", status_code=303)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})