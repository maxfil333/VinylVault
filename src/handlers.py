from fastapi import Request, status, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import RedirectResponse, JSONResponse


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(StarletteHTTPException)
    async def global_http_exception_handler(request: Request, exc: StarletteHTTPException):
        # HTML-страницы: уводим на логин. API: оставляем JSON 401 для fetch/клиентов.
        if (
            exc.status_code == status.HTTP_401_UNAUTHORIZED
            and not request.url.path.startswith("/api/")
        ):
            return RedirectResponse(url="/login", status_code=303)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def form_validation_handler(request: Request, exc: RequestValidationError):
        if request.method == "POST" and request.url.path == "/register":
            return RedirectResponse(url="/register?error=email", status_code=303)
        if request.method == "POST" and request.url.path == "/login":
            return RedirectResponse(url="/login?error=invalid", status_code=303)
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})
