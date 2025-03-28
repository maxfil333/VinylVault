import uvicorn
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pymongo.collection import Collection
from pydantic import EmailStr

from src.models import VV_Album, VV_User
from src.handlers import PageNotFoundHandler
from src.album_info import album_search, get_album_info
from src.database import vinyl_vault_users, add_user, is_in_collection
from src.utils import load_html
from src.pages import generate_user_page
from src.config import WEBSITE_DIR, USERS_DIR

app = FastAPI()
# uvicorn src.main:app --reload

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно ограничить)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

users_collection_dependency = Annotated[Collection, Depends(vinyl_vault_users)]


# ____________________________________ API ____________________________________

@app.get("/api/search/albums/{album_name}", response_model=list[VV_Album])
def search_album(album_name: str):
    """ Возвращает список найденных альбомов по запросу пользователя """

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
def add_album(user_id: str, album: VV_Album, users_collection: users_collection_dependency):
    """
        Добавляет альбом в базу пользователя:
        1) инициализирует объект VV_Album (из параметров id, artist, album)
        2) находит через api доп. информацию по альбому
        3) добавляет к VV_Album найденную информацию (cover urls)
        4) добавляет альбом в DB
    """

    album_info = get_album_info(artist_name=album.artist_name, album_name=album.album_name)['album']

    album.cover_url = album_info['image'][-1]['#text']
    album.cover_url_reserve = album_info['image'][-2]['#text']

    users_collection.update_one(
        filter={"user_id": user_id},
        update={"$push": {"albums": album.model_dump()}}
    )
    return {"message": "Альбом добавлен", "album": album}


# TODO: обработать случаи когда два одинаковых альбома, удалять только один (можно каждому альбому присваивать id)
#  и идентифицировать их по id а не по комбинации album_name artist_name
@app.delete("/api/users/{user_id}/albums/delete/{album_id}")
def delete_album(user_id: str, album_id: str, users_collection: users_collection_dependency):
    """ Удаляет альбом из базы пользователя """

    result = users_collection.update_one(
        filter={"user_id": user_id},
        update={"$pull": {"albums": {"album_id": album_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Альбом не найден или не удален")
    return {"message": "Альбом удален", "album": album_id}


@app.get("/api/users/{user_id}/albums/all/", response_model=list[VV_Album])
async def get_user_albums(user_id: str, users_collection: users_collection_dependency):
    """ Возвращает список альбомов пользователя из базы """

    user: dict = users_collection.find_one({"user_id": user_id})

    if user:
        return VV_User.model_validate(user).albums


# ___________________________ REGISTER and LOGIN ___________________________

@app.post("/register", response_class=HTMLResponse)
async def register(users_collection: users_collection_dependency,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """

    try:
        user = VV_User(username=username, password=password, email=email)
        if is_in_collection(field='username', value=user.username, collection=users_collection):
            raise HTTPException(status_code=409, detail="User already exists")
        new_user = add_user(users_collection, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")

    # Генерируем страницу для нового пользователя
    await generate_user_page(user_id=new_user.inserted_id, username=username)

    # Перенаправляем пользователя на его страницу.
    # Если страница генерируется в виде файла /users/{user_id}.html, то URL может выглядеть так:
    return RedirectResponse(url=f"/static/data/users/{new_user.inserted_id}.html", status_code=303)


@app.post("/login")
async def login(users_collection: users_collection_dependency,
                username: str = Form(...), password: str = Form(...)):
    """ Обработчик логина. Принимает данные из HTML-формы и возвращает пользователя из базы данных. """

    try:
        user = users_collection.find_one({"username": username, "password": password})
        if user:
            return RedirectResponse(url=f"/static/data/users/{user.get('user_id')}.html", status_code=303)
        else:
            HTTPException(status_code=401, detail="Invalid login or password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")


# _____________________________ HTMLResponse _____________________________

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

# Подключаем Middleware
app.add_middleware(PageNotFoundHandler, vinyl_vault_users=vinyl_vault_users())

if __name__ == '__main__':
    uvicorn.run(app)
