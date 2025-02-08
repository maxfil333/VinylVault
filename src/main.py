import os
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pymongo.collection import Collection
from pydantic import EmailStr

from src.models import Album, User
from src.album_info import album_search
from src.database import vinyl_vault_users, add_user, is_in_collection
from src.utils import load_html

app = FastAPI()
# uvicorn src.main:app --reload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(BASE_DIR, "..", "website")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно ограничить)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

albums = []


@app.post("/albums/")
def add_album(album: Album):
    albums.append(album)
    return {"message": "Альбом добавлен", "album": album}


@app.delete("/albums/")
def delete_album(album: Album):
    albums.remove(album)
    return {"message": "Альбом удален", "album": album}


@app.get("/albums/")
def show_albums():
    return {"albums": [albums]}


@app.get("/albums/{album_name}")
def search_album(album_name: str):
    search_results = album_search(album_name)
    return [{"name": x["name"], "artist": x["artist"], "image": x["image"]} for x in search_results]


users_collection_dependency = Annotated[Collection, Depends(vinyl_vault_users)]


@app.post("/register")
async def register(users_collection: users_collection_dependency,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """

    try:
        user = User(username=username, password=password, email=email)
        if is_in_collection(field='username', value=user.username, collection=users_collection):
            raise HTTPException(status_code=409, detail="User already exists")
        add_user(users_collection, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")

    return {
        "message": "Пользователь успешно зарегистрирован",
        "user_id": user.id
    }


@app.post("/login")
async def register(users_collection: users_collection_dependency,
                   username: str = Form(...), password: str = Form(...)):
    """ Обработчик логина. Принимает данные из HTML-формы и возвращает пользователя из базы данных. """

    try:
        data = {"username": username, "password": password}
        result = users_collection.find_one(data)
        if result:
            return result
        else:
            HTTPException(status_code=401, detail="Invalid login or password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")


# ________________________ HTMLResponse ________________________

@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page():
    content = load_html("welcome.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    content = load_html("register.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    content = load_html("login.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


app.mount("/static", StaticFiles(directory=WEBSITE_DIR), name="static")
