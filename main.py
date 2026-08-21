import time
import uuid
import uvicorn
import asyncio
import re
from contextlib import asynccontextmanager
from typing import Annotated, Optional
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, Form, Cookie, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import EmailStr
from pymongo.errors import DuplicateKeyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import cfg
from src.models import VV_Album, VV_User, SearchResults, AlbumsLayout
from src.handlers import register_exception_handlers
from src.lastfm_api.album_info import album_search, album_getinfo
from src.lastfm_api.artist_info import artist_top_albums
from src.database import get_users_collection, add_user, is_in_collection, pick_random_username
from src.database import get_session_cookies_collection, add_session, init_database, close_database, ping_database
from src.utils.utils import load_html
from src.utils.logger import logger
from src.pages import render_user_page
from src.cdn.s3_avatars import coalesce_avatar_url, upload_user_avatar_to_s3
from src.cdn.data_cdn import build_vv_theme_css, patch_html_with_cdn_assets
from src.utils.avatar_upload import detect_image_content_type, read_upload_up_to
from src.utils.passwords import hash_password, verify_password
from src.utils.ttl_cache import TTLCache

AVATAR_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
AVATAR_ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
    await close_database()


app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if cfg.ENABLE_DOCS else None,
    redoc_url="/redoc" if cfg.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if cfg.ENABLE_DOCS else None,
)
register_exception_handlers(app)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Запуск без docker: uvicorn main:app --reload

users_collection_dep = Annotated[AsyncIOMotorCollection, Depends(get_users_collection)]
session_cookies_dep = Annotated[AsyncIOMotorCollection, Depends(get_session_cookies_collection)]

SESSION_COOKIES_KEY = 'vv_session_cookie'
# Поиск открыт и гостям (welcome-страница), поэтому квоту Last.fm берегут лимиты по IP и кэш
SEARCH_ALBUMS_CACHE = TTLCache(ttl_sec=cfg.SEARCH_CACHE_TTL_SEC)
SEARCH_MIXED_CACHE = TTLCache(ttl_sec=cfg.SEARCH_CACHE_TTL_SEC)
PUBLIC_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
RESERVED_PROFILE_PATHS = {
    "",
    "user",
}


# ___________________________ REGISTER | LOGIN | LOGOUT ___________________________

def _cookie_secure(request: Request) -> bool:
    """ Secure ставим по настройке; схема запроса верна только при доверенном прокси. """
    return cfg.COOKIE_SECURE or request.url.scheme == "https"


async def verify_login_password(username: str, password: str,
                                users_collection: users_collection_dep) -> Optional[VV_User]:
    """ Проверяет логин и пароль пользователя и возвращает пользователя из базы данных. """
    user_doc = await users_collection.find_one({"username": username})
    if not user_doc or not verify_password(password, user_doc.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid login or password")
    return VV_User.model_validate(user_doc)


def generate_session_id() -> str:
    """ Генерация случайного id сессии """
    return str(uuid.uuid4().hex) + str(time.time_ns())


async def get_session_data(
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
) -> dict:
    """ Получить информацию о сессии по Cookie """
    logger.debug("Получил куку сессии" if session_id else "Куки сессии нет")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    session = await session_cookies_collection.find_one({'session_id': session_id})
    return session or {}


async def _cookie_create_and_set(
    session_cookies: AsyncIOMotorCollection,
    user: VV_User,
    request: Request,
) -> Response:
    """ Создаем сессию и устанавливаем cookie, затем редиректим на канонический URL профиля """
    session_id = generate_session_id()
    await add_session(collection=session_cookies, session_id=session_id, user=user)
    response = RedirectResponse(url=_build_profile_path(user.username), status_code=303)
    response.set_cookie(
        key=SESSION_COOKIES_KEY,
        value=session_id,
        httponly=True,
        max_age=cfg.SESSION_TTL_SEC,
        samesite="lax",
        secure=_cookie_secure(request),
    )
    logger.debug("Установлена кука сессии")
    return response


def _build_profile_path(username: str) -> str:
    return f"/user/{quote(username, safe='')}"


def _is_public_profile_username(username: str) -> bool:
    normalized = username.strip()
    if not normalized:
        return False
    if normalized.lower() in RESERVED_PROFILE_PATHS:
        return False
    return bool(PUBLIC_USERNAME_RE.fullmatch(normalized))


@app.post("/register", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def register(request: Request, users_collection: users_collection_dep, session_cookies: session_cookies_dep,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """
    if not _is_public_profile_username(username):
        return RedirectResponse(url="/register?error=badusername", status_code=303)
    if not password.strip():
        return RedirectResponse(url="/register?error=password", status_code=303)
    if await is_in_collection(field='username', value=username, collection=users_collection):
        return RedirectResponse(url="/register?error=exists", status_code=303)
    if await is_in_collection(field='email', value=str(email), collection=users_collection):
        return RedirectResponse(url="/register?error=emailused", status_code=303)
    try:
        user = VV_User(username=username, password=hash_password(password), email=email)
        new_user = await add_user(users_collection, user)
        logger.debug(f'New user is created: {new_user}')
    except DuplicateKeyError:
        return RedirectResponse(url="/register?error=exists", status_code=303)
    except Exception:
        logger.exception("Ошибка при регистрации пользователя")
        return RedirectResponse(url="/register?error=server", status_code=303)
    # Создаем сессию и устанавливаем cookie, чтобы /me открыл страницу текущего пользователя
    response = await _cookie_create_and_set(session_cookies=session_cookies, user=user, request=request)
    return response


@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, users_collection: users_collection_dep, session_cookies: session_cookies_dep,
                username: str = Form(...), password: str = Form(...)):
    """ Обработчик логина. Принимает данные из HTML-формы и возвращает пользователя из базы данных. """
    if not password.strip():
        return RedirectResponse(url="/login?error=invalid", status_code=303)
    try:
        user = await verify_login_password(username, password, users_collection)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse(url="/login?error=invalid", status_code=303)
        raise
    # Создаем сессию и устанавливаем cookie, чтобы /me открыл страницу текущего пользователя
    response = await _cookie_create_and_set(session_cookies=session_cookies, user=user, request=request)
    return response


@app.post("/logout")
async def logout(request: Request, session_cookies: session_cookies_dep,
                 session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None)):
    """ Выход пользователя: удаляет сессию из базы данных и очищает cookie """
    if session_id:
        # Удаляем сессию из базы данных
        await session_cookies.delete_one({'session_id': session_id})
        logger.debug("Удалена сессия")

    # Создаем ответ с редиректом на welcome и очищаем cookie
    response = RedirectResponse(url="/welcome", status_code=303)
    response.delete_cookie(
        key=SESSION_COOKIES_KEY,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
    )
    return response


# _____________________________ PAGES _____________________________

@app.get("/me", response_class=HTMLResponse)
async def my_page(
    session_data: dict = Depends(get_session_data),
):
    """ Удобный редирект на страницу текущего пользователя """
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    username = session_data.get("username")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    return RedirectResponse(url=_build_profile_path(username), status_code=303)


@app.get("/random-user")
@limiter.limit("30/minute")
async def random_user_page(
    request: Request,
    users_collection: users_collection_dep,
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
):
    """ Редирект на профиль случайного пользователя (свой профиль пропускаем). """
    exclude_username = None
    if session_id:
        session = await session_cookies_collection.find_one({'session_id': session_id}) or {}
        exclude_username = session.get("username")

    username = await pick_random_username(users_collection, exclude_username=exclude_username)
    if not username:
        logger.debug("Случайный пользователь не найден")
        return RedirectResponse(url="/welcome", status_code=303)

    return RedirectResponse(url=_build_profile_path(username), status_code=303)


@app.get("/user/{username}", response_class=HTMLResponse)
async def user_page_by_username(
    username: str,
    users_collection: users_collection_dep,
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
):
    """ Публичная страница пользователя по username. """
    user_doc = await users_collection.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    session_data = {}
    if session_id:
        session_data = await session_cookies_collection.find_one({'session_id': session_id}) or {}

    avatar_url = coalesce_avatar_url(user_doc.get("avatar_url"))
    content = render_user_page(
        username=user_doc["username"],
        avatar_url=avatar_url,
        is_owner=session_data.get("user_id") == user_doc.get("user_id"),
        is_authenticated=bool(session_data),
    )

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return HTMLResponse(content=content, headers=headers)


# _____________________________ HTMLResponse _____________________________

@app.get("/", response_class=HTMLResponse)
async def default_page(
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
):
    if session_id:
        session = await session_cookies_collection.find_one({'session_id': session_id})
        if session:
            return RedirectResponse(url=_build_profile_path(session["username"]), status_code=303)
    return RedirectResponse(url="/welcome", status_code=303)


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page():
    content = patch_html_with_cdn_assets(load_html("welcome.html", cfg.WEBSITE_DIR))
    return HTMLResponse(content=content)


@app.api_route("/explore", methods=["GET", "POST"])
async def explore(session_data: dict = Depends(get_session_data)):
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return RedirectResponse(url=_build_profile_path(session_data["username"]), status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    content = patch_html_with_cdn_assets(load_html("register.html", cfg.WEBSITE_DIR))
    return HTMLResponse(content=content)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    content = patch_html_with_cdn_assets(load_html("login.html", cfg.WEBSITE_DIR))
    return HTMLResponse(content=content)


@app.get("/static/vv-data-theme.css")
async def vv_data_theme_css():
    """Переменные фона/плейсхолдера с CDN (подключается до styles.css)."""
    return Response(content=build_vv_theme_css(), media_type="text/css; charset=utf-8")


# ____________________________________ API ____________________________________

@app.get("/api/search/albums/{album_name}", response_model=list[VV_Album])
@limiter.limit("20/minute")
async def search_album(request: Request, album_name: str):
    """ Возвращает список найденных альбомов по запросу пользователя (legacy для фронта) """
    cached = SEARCH_ALBUMS_CACHE.get(album_name.strip().lower())
    if cached is not None:
        return cached

    search_results = await album_search(album_name)
    albums: list[VV_Album] = []
    for x in search_results:
        albums.append(VV_Album.model_validate({
            "album_name": x.get("name", ""),
            "artist_name": x.get("artist", ""),
            "cover_url": (x.get("image", [])[-1] or {}).get("#text", "") if x.get("image") else "",
            "cover_url_reserve": (x.get("image", [])[-2] or {}).get("#text", "") if x.get("image") and len(
                x.get("image")) > 1 else ""
        }))
    SEARCH_ALBUMS_CACHE.set(album_name.strip().lower(), albums)
    return albums


@app.get("/api/search/mixed/{query}", response_model=SearchResults)
@limiter.limit("30/minute")
async def search_mixed(request: Request, query: str):
    """ Выполняет параллельный поиск: по имени альбома и по топ-альбомам исполнителя. Возвращает сгруппировано. """
    cached = SEARCH_MIXED_CACHE.get(query.strip().lower())
    if cached is not None:
        return cached

    # Асинхронно запускаем оба запроса к внешнему API
    album_search_results, artist_top_results = await asyncio.gather(
        album_search(query),
        artist_top_albums(query)
    )
    albums_group: list[VV_Album] = []
    for x in album_search_results:
        albums_group.append(VV_Album.model_validate({
            "album_name": x.get("name", ""),
            "artist_name": x.get("artist", ""),
            "cover_url": (x.get("image", [])[-1] or {}).get("#text", "") if x.get("image") else "",
            "cover_url_reserve": (x.get("image", [])[-2] or {}).get("#text", "") if x.get("image") and len(
                x.get("image")) > 1 else ""
        }))

    # artist_top_albums
    artist_group: list[VV_Album] = []
    if artist_top_results:
        for x in artist_top_results:
            # структура top_albums: { name, artist: { name }, image: [...] }
            artist_name = x.get("artist", {}).get("name") if isinstance(x.get("artist"), dict) else x.get("artist", "")
            artist_group.append(VV_Album.model_validate({
                "album_name": x.get("name", ""),
                "artist_name": artist_name or "",
                "cover_url": (x.get("image", [])[-1] or {}).get("#text", "") if x.get("image") else "",
                "cover_url_reserve": (x.get("image", [])[-2] or {}).get("#text", "") if x.get("image") and len(
                    x.get("image")) > 1 else ""
            }))

    results = SearchResults(albums=albums_group, artist_top_albums=artist_group)
    SEARCH_MIXED_CACHE.set(query.strip().lower(), results)
    return results


@app.post("/api/users/{user_id}/albums/add/")
async def add_album(
    user_id: str,
    album: VV_Album,
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """
        Добавляет альбом в базу пользователя:
        1) инициализирует объект VV_Album (из параметров id, artist, album)
        2) находит через api доп. информацию по альбому
        3) добавляет к VV_Album найденную информацию (cover urls)
        4) устанавливает порядок альбома (последний в списке)
        5) добавляет альбом в DB
    """
    # Проверяем, что user_id из URL соответствует user_id из сессии
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    raw = await album_getinfo(artist_name=album.artist_name, album_name=album.album_name)
    album_info = raw.get("album") if isinstance(raw, dict) else None
    if not album_info:
        detail = raw.get("error", "Альбом не найден в Last.fm") if isinstance(raw, dict) else "Альбом не найден в Last.fm"
        raise HTTPException(status_code=404, detail=detail)

    images = album_info.get("image") or []
    album.cover_url = (images[-1] or {}).get("#text", "") if images else ""
    album.cover_url_reserve = (images[-2] or {}).get("#text", "") if len(images) > 1 else ""

    # Получаем текущее количество альбомов пользователя для установки порядка
    user = await users_collection.find_one({"user_id": user_id})
    current_album_count = len(user.get("albums", [])) if user else 0
    album.order = current_album_count

    await users_collection.update_one(
        filter={"user_id": user_id},
        update={"$push": {"albums": album.model_dump()}}
    )
    return {"message": "Альбом добавлен", "album": album}


@app.delete("/api/users/{user_id}/albums/delete/{album_id}")
async def delete_album(
    user_id: str,
    album_id: str,
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """ Удаляет альбом из базы пользователя """
    # Проверяем, что user_id из URL соответствует user_id из сессии
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await users_collection.update_one(
        filter={"user_id": user_id},
        update={"$pull": {"albums": {"album_id": album_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Альбом не найден или не удален")
    return {"message": "Альбом удален", "album": album_id}


@app.get("/api/users/{user_id}/albums/all/", response_model=list[VV_Album])
async def get_user_albums(
    user_id: str,
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """ Возвращает список альбомов пользователя из базы, отсортированных по порядку """
    logger.info(f"{user_id=}")

    # Проверяем, что user_id из URL соответствует user_id из сессии
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    user: dict = await users_collection.find_one({"user_id": user_id})

    if user:
        albums = VV_User.model_validate(user).albums
        # Сортируем альбомы по полю order
        albums.sort(key=lambda x: x.order)
        return albums
    return []


@app.put("/api/users/{user_id}/albums/reorder/")
async def reorder_albums(
    user_id: str,
    album_orders: list[dict],
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """ Обновляет порядок альбомов пользователя """
    logger.info(f"Reordering albums for user_id: {user_id!r}")

    # Проверяем, что user_id из URL соответствует user_id из сессии
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Валидируем входные данные
    if not album_orders:
        raise HTTPException(status_code=400, detail="Список порядков альбомов не может быть пустым")
    
    # Обновляем порядок каждого альбома
    for album_order in album_orders:
        album_id = album_order.get("album_id")
        new_order = album_order.get("order")
        
        if album_id is None or new_order is None:
            raise HTTPException(status_code=400, detail="Неверный формат данных: требуется album_id и order")
        
        # Обновляем порядок конкретного альбома
        result = await users_collection.update_one(
            filter={"user_id": user_id, "albums.album_id": album_id},
            update={"$set": {"albums.$.order": new_order}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Альбом с ID {album_id} не найден")
    
    return {"message": "Порядок альбомов успешно обновлен"}


@app.put("/api/users/{user_id}/albums/layout/", response_model=list[VV_Album])
async def save_albums_layout(
    user_id: str,
    layout: AlbumsLayout,
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """
        Применяет удаления и порядок альбомов одной записью в документ пользователя.
        Частичный сбой невозможен: либо запись прошла целиком, либо коллекция осталась прежней.
    """
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    user_doc = await users_collection.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    albums = VV_User.model_validate(user_doc).albums
    deleted = set(layout.deleted_album_ids)
    kept = [album for album in albums if album.album_id not in deleted]

    # Альбомы, которых нет в присланном порядке (добавлены из другой вкладки), уходят в конец
    positions = {album_id: index for index, album_id in enumerate(layout.order)}
    kept.sort(key=lambda album: (positions.get(album.album_id, len(positions)), album.order))
    for index, album in enumerate(kept):
        album.order = index

    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"albums": [album.model_dump() for album in kept]}},
    )
    logger.debug(f"Сохранена коллекция: удалено {len(albums) - len(kept)}, осталось {len(kept)}")
    return kept


@app.get("/api/auth/check")
async def check_auth(
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
):
    """ Проверяет статус авторизации пользователя. Возвращает is_authenticated: true/false """
    logger.debug("Проверка авторизации")
    if not session_id:
        return {"is_authenticated": False}
    session = await session_cookies_collection.find_one({'session_id': session_id})
    if session:
        return {"is_authenticated": True}
    return {"is_authenticated": False}


@app.get("/api/me/userid")
async def get_current_user_id(session_data: dict = Depends(get_session_data)):
    """ Для запроса с фронта. Возвращает user_id по Cookie"""
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    return {"user_id": session_data["user_id"]}


@app.get("/api/me/profile")
async def get_current_user_profile(
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
):
    """ Профиль текущего пользователя: имя и URL аватара (для отображения на странице /me). """
    user_id = session_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    user_doc = await users_collection.find_one({"user_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "user_id": user_id,
        "username": user_doc.get("username", session_data.get("username", "")),
        "avatar_url": coalesce_avatar_url(user_doc.get("avatar_url")),
        "profile_path": _build_profile_path(user_doc.get("username", session_data.get("username", ""))),
    }


@app.get("/api/profiles/{username}")
async def get_public_user_profile(
    username: str,
    users_collection: users_collection_dep,
):
    """ Публичный профиль пользователя по username. """
    user_doc = await users_collection.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "user_id": user_doc["user_id"],
        "username": user_doc["username"],
        "avatar_url": coalesce_avatar_url(user_doc.get("avatar_url")),
        "profile_path": _build_profile_path(user_doc["username"]),
    }


@app.get("/api/profiles/{username}/albums", response_model=list[VV_Album])
async def get_public_user_albums(
    username: str,
    users_collection: users_collection_dep,
):
    """ Возвращает публичный список альбомов пользователя по username. """
    user_doc = await users_collection.find_one({"username": username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    albums = VV_User.model_validate(user_doc).albums
    albums.sort(key=lambda x: x.order)
    return albums


@app.post("/api/users/{user_id}/avatar")
async def upload_user_avatar(
    user_id: str,
    users_collection: users_collection_dep,
    session_data: dict = Depends(get_session_data),
    file: UploadFile = File(...),
):
    """ Загрузка нового аватара (только для своей учётной записи). """
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    data = await read_upload_up_to(file, AVATAR_UPLOAD_MAX_BYTES)
    content_type = detect_image_content_type(data)
    if content_type is None or content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Файл не является допустимым изображением")

    ext = AVATAR_ALLOWED_TYPES[content_type]
    avatar_url = await upload_user_avatar_to_s3(user_id, data, content_type, ext)
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"avatar_url": avatar_url}},
    )
    return {"avatar_url": avatar_url}


@app.get("/health")
async def health():
    """ Проба для контейнера и прокси: 200 только когда база отвечает. """
    if not await ping_database():
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "down"})
    return {"status": "ok", "database": "up"}


# ____________________________________ FastAPI config ____________________________________

# если кто-то запрашивает http://<your-domain>/static/somefile.png,
# FastAPI ищет файл по пути WEBSITE_DIR/somefile.png на диске.
# ! если прописывать путь без "/" в начале (например img src="static/...") - он будет не абсолютным, а относительным
app.mount("/static", StaticFiles(directory=cfg.WEBSITE_DIR))


if __name__ == "__main__":
    # forwarded_allow_ips: без доверенного прокси схема запроса и IP клиента приходят от прокси,
    # из-за чего ломаются флаг Secure у cookie и лимиты по IP.
    uvicorn.run(
        app,
        host=cfg.APP_HOST,
        port=cfg.APP_PORT,
        proxy_headers=True,
        forwarded_allow_ips=cfg.FORWARDED_ALLOW_IPS,
    )
