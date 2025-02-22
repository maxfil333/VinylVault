import os
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pymongo.collection import Collection
from pydantic import EmailStr


from src.models import Album, User
from src.album_info import album_search
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


@app.post("/register", response_class=HTMLResponse)
async def register(users_collection: users_collection_dependency,
                   username: str = Form(...), password: str = Form(...), email: EmailStr = Form(...)):
    """ Обработчик регистрации. Принимает данные из HTML-формы и добавляет нового пользователя в базу данных. """

    try:
        user = User(username=username, password=password, email=email)
        if is_in_collection(field='username', value=user.username, collection=users_collection):
            raise HTTPException(status_code=409, detail="User already exists")
        new_user = add_user(users_collection, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при регистрации пользователя: {e}")

    # Генерируем страницу для нового пользователя
    generate_user_page(user_id=new_user.inserted_id, username=username)

    # Перенаправляем пользователя на его страницу.
    # Если страница генерируется в виде файла /users/{user_id}.html, то URL может выглядеть так:
    return RedirectResponse(url=f"user/{new_user.inserted_id}.html", status_code=303)



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
app.mount("/static", StaticFiles(directory=WEBSITE_DIR), name="static")
app.mount("/user", StaticFiles(directory=USERS_DIR), name="user")
