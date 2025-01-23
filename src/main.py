from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo.collection import Collection

from src.models import Album
from src.album_info import album_search
from src.database import vinyl_vault_users


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


vinyl_vault_users_dependency = Annotated[Collection, Depends(vinyl_vault_users)]


@app.post("/register/")
async def register_user(username: str, password: str, users_collection: vinyl_vault_users_dependency):
    if users_collection.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="User already exists")

    user = {"username": username, "password": password}
    users_collection.insert_one(user)
    return {"message": "User registered successfully"}
