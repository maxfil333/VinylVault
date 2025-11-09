import os
import time
import uuid
import uvicorn
import asyncio
from typing import Annotated, Optional, Literal
from fastapi import FastAPI, Depends, HTTPException, Form, Cookie, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import EmailStr

from src.models import VV_Album, VV_User, SearchResults
from src.handlers import PageNotFoundHandler, register_exception_handlers
from src.album_info import album_search, album_getinfo, album_search_async
from src.artist_info import artist_top_albums_async
from src.database import vinyl_vault_users, add_user, is_in_collection
from src.database import session_cookies, add_session, init_database, close_database
from src.utils import load_html
from src.pages import generate_user_page
from src.config import WEBSITE_DIR
from src.logger import logger

app = FastAPI()
register_exception_handlers(app)

# uvicorn src.main:app --reload

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно ограничить)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

users_collection_dep = Annotated[AsyncIOMotorCollection, Depends(vinyl_vault_users)]
session_cookies_dep = Annotated[AsyncIOMotorCollection, Depends(session_cookies)]

SESSION_COOKIES_KEY = 'vv_session_cookie'


# ___________________________ REGISTER | LOGIN | LOGOUT ___________________________

async def verify_login_password(username: str, password: str,
                                users_collection: users_collection_dep) -> Optional[VV_User]:
    """ Проверяет логин и пароль пользователя и возвращает пользователя из базы данных. """
    logger.info("")
    if user := await users_collection.find_one({"username": username, "password": password}):
        return VV_User.model_validate(user)
    raise HTTPException(status_code=401, detail="Invalid login or password")


def generate_session_id() -> str:
    """ Генерация случайного id сессии """
    logger.info("")
    return str(uuid.uuid4().hex) + str(time.time_ns())


async def get_session_data(
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
) -> dict:
    """ Получить информацию о сессии по Cookie """
    logger.debug(f"Получил куку: {session_id!r}")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    session = await session_cookies_collection.find_one({'session_id': session_id})
    return session or {}


async def _cookie_create_and_set(session_cookies: AsyncIOMotorCollection, user: VV_User) -> Response:
    """ Создаем сессию и устанавливаем cookie, чтобы /me открыл страницу текущего пользователя """
    session_id = generate_session_id()
    await add_session(collection=session_cookies, session_id=session_id, user=user)
    response = RedirectResponse(url=f"/me", status_code=303)
    response.set_cookie(key=SESSION_COOKIES_KEY, value=session_id)
    logger.debug(f"Установлена кука: {session_id!r}")
    return response


@app.post("/register", response_class=HTMLResponse)
async def register(users_collection: users_collection_dep, session_cookies: session_cookies_dep,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """
    logger.info("")
    try:
        user = VV_User(username=username, password=password, email=email)
        if await is_in_collection(field='username', value=user.username, collection=users_collection):
            raise HTTPException(status_code=409, detail="User already exists")
        new_user = await add_user(users_collection, user)
        logger.debug(f'New user is created: {new_user}')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")
    # Генерируем страницу для нового пользователя (имя файла совпадает с VV_User.user_id)
    await generate_user_page(user_id=user.user_id, username=username)
    # Создаем сессию и устанавливаем cookie, чтобы /me открыл страницу текущего пользователя
    response = await _cookie_create_and_set(session_cookies=session_cookies, user=user)
    return response


@app.post("/login")
async def login(users_collection: users_collection_dep, session_cookies: session_cookies_dep,
                username: str = Form(...), password: str = Form(...)):
    """ Обработчик логина. Принимает данные из HTML-формы и возвращает пользователя из базы данных. """
    logger.info("")
    user = await verify_login_password(username, password, users_collection)
    # Создаем сессию и устанавливаем cookie, чтобы /me открыл страницу текущего пользователя
    response = await _cookie_create_and_set(session_cookies=session_cookies, user=user)
    return response


@app.post("/logout")
async def logout(session_cookies: session_cookies_dep,
                 session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None)):
    """ Выход пользователя: удаляет сессию из базы данных и очищает cookie """
    logger.info("")
    if session_id:
        # Удаляем сессию из базы данных
        await session_cookies.delete_one({'session_id': session_id})
        logger.debug(f"Удалена сессия: {session_id!r}")

    # Создаем ответ с редиректом на welcome и очищаем cookie
    response = RedirectResponse(url="/welcome", status_code=303)
    response.delete_cookie(key=SESSION_COOKIES_KEY)
    return response


# _____________________________ PAGES _____________________________

@app.get("/me")
async def my_page(session_data: dict = Depends(get_session_data)):
    """ Страница пользователя """
    logger.info("")

    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    user_id, username = session_data["user_id"], session_data["username"]
    file_path = os.path.join(WEBSITE_DIR, "data", "users", f"{user_id}.html")
    if not os.path.exists(file_path):
        # Генерируем страницу для нового пользователя (имя файла совпадает с VV_User.user_id)
        await generate_user_page(user_id=user_id, username=username)

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",  # запрет на хранение содержимого в кеше
        "Pragma": "no-cache",  # устаревший заголовок HTTP/1.0
        "Expires": "0"  # устаревший заголовок HTTP/1.0
    }
    return FileResponse(path=file_path, media_type="text/html", headers=headers)


# _____________________________ HTMLResponse _____________________________

@app.get("/", response_class=HTMLResponse)
async def default_page():
    response = RedirectResponse(url=f"/welcome")
    return response


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page():
    content = load_html("welcome.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/testuser", response_class=HTMLResponse)
async def testuser():
    content = load_html("user_page_example.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    content = load_html("register.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    content = load_html("login.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


# ____________________________________ API ____________________________________

@app.get("/api/search/albums/{album_name}", response_model=list[VV_Album])
def search_album(album_name: str):
    """ Возвращает список найденных альбомов по запросу пользователя (legacy для фронта) """
    logger.info("")
    search_results = album_search(album_name)
    albums: list[VV_Album] = []
    for x in search_results:
        albums.append(VV_Album.model_validate({
            "album_name": x.get("name", ""),
            "artist_name": x.get("artist", ""),
            "cover_url": (x.get("image", [])[-1] or {}).get("#text", "") if x.get("image") else "",
            "cover_url_reserve": (x.get("image", [])[-2] or {}).get("#text", "") if x.get("image") and len(
                x.get("image")) > 1 else ""
        }))
    return albums


@app.get("/api/search/mixed/{query}", response_model=SearchResults)
async def search_mixed(query: str):
    """ Выполняет параллельный поиск: по имени альбома и по топ-альбомам исполнителя. Возвращает сгруппировано. """
    logger.info("")

    # Асинхронно запускаем оба запроса к внешнему API
    album_search_results, artist_top_results = await asyncio.gather(
        album_search_async(query),
        artist_top_albums_async(query)
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

    return SearchResults(albums=albums_group, artist_top_albums=artist_group)


# TODO: scripts.js: sendAlbumToServer --> вместо дефолтного _id брать логин+пароль из авторизационных данных.
#  add_album.users_collection.update_one делать только если юзер с таким логин+пароль существует

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
    logger.info("")

    # Проверяем, что user_id из URL соответствует user_id из сессии
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    album_info = album_getinfo(artist_name=album.artist_name, album_name=album.album_name)['album']

    album.cover_url = album_info['image'][-1]['#text']
    album.cover_url_reserve = album_info['image'][-2]['#text']

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
    logger.info("")

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


@app.get("/api/auth/check")
async def check_auth(
    session_cookies_collection: session_cookies_dep,
    session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None),
):
    """ Проверяет статус авторизации пользователя. Возвращает is_authenticated: true/false """
    logger.debug(f"Проверка авторизации: {session_id!r}")
    if not session_id:
        return {"is_authenticated": False}
    session = await session_cookies_collection.find_one({'session_id': session_id})
    if session:
        return {"is_authenticated": True}
    return {"is_authenticated": False}


@app.get("/api/me/userid")
async def get_current_user_id(session_data: dict = Depends(get_session_data)):
    """ Для запроса с фронта. Возвращает user_id по Cookie"""
    logger.info("")

    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    return {"user_id": session_data["user_id"]}


# ____________________________________ FastAPI config ____________________________________

# если кто-то запрашивает http://<your-domain>/static/somefile.png,
# FastAPI ищет файл по пути WEBSITE_DIR/somefile.png на диске.
# ! если прописывать путь без "/" в начале (например img src="static/...") - он будет не абсолютным, а относительным
app.mount("/static", StaticFiles(directory=WEBSITE_DIR))


async def setup_app():
    # Инициализируем подключение к MongoDB
    await init_database()

    # Подключаем Middleware
    users_collection = await vinyl_vault_users()  # Дожидаемся коллекции
    app.add_middleware(PageNotFoundHandler, vinyl_vault_users=users_collection)
    return app


if __name__ == "__main__":
    import atexit


    async def cleanup():
        await close_database()


    # Регистрируем функцию очистки для выполнения при завершении
    atexit.register(lambda: asyncio.run(cleanup()))

    # ___ DEBUG ___
    import glob


    def cleanup_users():
        for f in glob.glob('../website/data/users/*.html'):
            os.unlink(f)


    atexit.register(lambda: cleanup_users())
    # ___ DEBUG ___

    loop = asyncio.new_event_loop()
    loop.run_until_complete(setup_app())
    uvicorn.run(app)

# todo: редирект с главной на welcome если нет куки, на my если есть куки

# todo: https://chatgpt.com/share/686a8248-0344-8010-9dd2-4ef466f31b03
# /my + удалить из свободного доступа users

# todo: перенести users из website в protected
