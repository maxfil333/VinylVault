import os
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pymongo.collection import Collection
from pydantic import ValidationError

from src.models import Album, User
from src.album_info import album_search
from src.database import vinyl_vault_users, add_user
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


vinyl_vault_users_dependency = Annotated[Collection, Depends(vinyl_vault_users)]


@app.post("/register/")
async def register_user(username: str, password: str, users_collection: vinyl_vault_users_dependency):
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=409, detail="User already exists")

    try:
        add_user(users_collection, User(**{"username": username, "password": password}))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"User data is invalid: {e}")

    return {"message": "User registered successfully"}


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page():
    content = load_html("welcome.html", WEBSITE_DIR)
    return HTMLResponse(content=content)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    content = load_html("login.html", WEBSITE_DIR)
    return HTMLResponse(content=content)
