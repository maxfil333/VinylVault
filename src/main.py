import os
import time
import uuid
import uvicorn
import asyncio
from typing import Annotated, Optional
from fastapi import FastAPI, Depends, HTTPException, Form, Cookie, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import EmailStr

from src.models import VV_Album, VV_User
from src.handlers import PageNotFoundHandler, register_exception_handlers
from src.album_info import album_search, get_album_info
from src.database import vinyl_vault_users, add_user, is_in_collection
from src.database import session_cookies, add_session
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


# ____________________________________ API ____________________________________

@app.get("/api/search/albums/{album_name}", response_model=list[VV_Album])
def search_album(album_name: str):
    """ Возвращает список найденных альбомов по запросу пользователя """
    logger.info("")
    search_results = album_search(album_name)
    albums = []
    for x in search_results:
        albums.append(VV_Album.model_validate({
            "album_name": x["name"],
            "artist_name": x["artist"],
            "cover_url": x["image"][-1]["#text"],
            "cover_url_reserve": x["image"][-2]["#text"]}))
    return albums


# TODO: scripts.js: sendAlbumToServer --> вместо дефолтного _id брать логин+пароль из авторизационных данных.
#  add_album.users_collection.update_one делать только если юзер с таким логин+пароль существует

@app.post("/api/users/{user_id}/albums/add/")
async def add_album(user_id: str, album: VV_Album, users_collection: users_collection_dep):
    """
        Добавляет альбом в базу пользователя:
        1) инициализирует объект VV_Album (из параметров id, artist, album)
        2) находит через api доп. информацию по альбому
        3) добавляет к VV_Album найденную информацию (cover urls)
        4) добавляет альбом в DB
    """
    logger.info("")

    album_info = get_album_info(artist_name=album.artist_name, album_name=album.album_name)['album']

    album.cover_url = album_info['image'][-1]['#text']
    album.cover_url_reserve = album_info['image'][-2]['#text']

    await users_collection.update_one(
        filter={"user_id": user_id},
        update={"$push": {"albums": album.model_dump()}}
    )
    return {"message": "Альбом добавлен", "album": album}


@app.delete("/api/users/{user_id}/albums/delete/{album_id}")
async def delete_album(user_id: str, album_id: str, users_collection: users_collection_dep):
    """ Удаляет альбом из базы пользователя """
    logger.info("")

    result = await users_collection.update_one(
        filter={"user_id": user_id},
        update={"$pull": {"albums": {"album_id": album_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Альбом не найден или не удален")
    return {"message": "Альбом удален", "album": album_id}


@app.get("/api/users/{user_id}/albums/all/", response_model=list[VV_Album])
async def get_user_albums(user_id: str, users_collection: users_collection_dep):
    """ Возвращает список альбомов пользователя из базы """
    logger.info("")

    user: dict = await users_collection.find_one({"user_id": user_id})

    if user:
        return VV_User.model_validate(user).albums


# ___________________________ REGISTER and LOGIN ___________________________

async def verify_login_password(username: str, password: str,
                                users_collection: users_collection_dep) -> Optional[VV_User]:
    """ Проверяет логин и пароль пользователя и возвращает пользователя из базы данных. """
    logger.info("")
    if user:= await users_collection.find_one({"username": username, "password": password}):
        return VV_User.model_validate(user)
    raise HTTPException(status_code=401, detail="Invalid login or password")


def generate_session_id() -> str:
    """ Генерация случайного id сессии """
    logger.info("")
    return str(uuid.uuid4().hex) + str(time.time_ns())


async def get_session_data(
        cookies_collection: session_cookies_dep,
        session_id: Optional[str] = Cookie(alias=SESSION_COOKIES_KEY, default=None)
) -> dict:
    """ Достать информацию по Cookie """
    logger.info(f"получил куку {session_id}")
    if session:= await cookies_collection.find_one({'session_id': session_id}):
        return session
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")


@app.post("/register", response_class=HTMLResponse)
async def register(users_collection: users_collection_dep,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """
    logger.info("")
    try:
        user = VV_User(username=username, password=password, email=email)
        if await is_in_collection(field='username', value=user.username, collection=users_collection):
            raise HTTPException(status_code=409, detail="User already exists")
        new_user = await add_user(users_collection, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")

    # Генерируем страницу для нового пользователя
    await generate_user_page(user_id=new_user.inserted_id, username=username)

    # Перенаправляем пользователя на его страницу.
    # Если страница генерируется в виде файла /users/{user_id}.html, то URL может выглядеть так:
    return RedirectResponse(url=f"/static/data/users/{new_user.inserted_id}.html", status_code=303)


@app.post("/login")
async def login(users_collection: users_collection_dep, session_cookies: session_cookies_dep, response: Response,
                username: str = Form(...), password: str = Form(...)):
    """ Обработчик логина. Принимает данные из HTML-формы и возвращает пользователя из базы данных. """
    logger.info("")
    user = await verify_login_password(username, password, users_collection)
    session_id = generate_session_id()
    session = await add_session(collection=session_cookies, session_id=session_id, user=user)
    response.set_cookie(SESSION_COOKIES_KEY, session_id)
    print(f"created cookie: {session}")

    response = RedirectResponse(url=f"/static/data/users/{user.user_id}.html", status_code=303)
    response.set_cookie(key=SESSION_COOKIES_KEY, value=session_id)
    return response


# _____________________________ PAGES _____________________________

@app.get("/my")
async def my_page(session_data: dict = Depends(get_session_data)):
    """ Страница пользователя """
    logger.info("")

    user_id = session_data["user_id"]
    file_path = os.path.join(WEBSITE_DIR, "data", "users", f"{user_id}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Page not found")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",  #  запрет на хранение содержимого в кеше
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


# если кто-то запрашивает http://<your-domain>/static/somefile.png,
# FastAPI ищет файл по пути WEBSITE_DIR/somefile.png на диске.
# ! если прописывать путь без "/" в начале (например img src="static/...") - он будет не абсолютным, а относительным
app.mount("/static", StaticFiles(directory=WEBSITE_DIR))


async def setup_app():
    # Подключаем Middleware
    users_collection = await vinyl_vault_users()  # Дожидаемся коллекции
    app.add_middleware(PageNotFoundHandler, vinyl_vault_users=users_collection)
    return app


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_app())
    uvicorn.run(app)

#todo: редирект с главной на welcome если нет куки, на my если есть куки

#todo: https://chatgpt.com/share/686a8248-0344-8010-9dd2-4ef466f31b03
# /my + удалить из свободного доступа users

#todo: перенести users из website в protected
