from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.models import Album
from src.album_info import album_search


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
def add_album(album: Album):
    albums.remove(album)
    return {"message": "Альбом удален", "album": album}


@app.get("/albums/")
def show_albums():
    return {"albums": [albums]}


@app.get("/albums/{album_name}")
def search_album(album_name: str):
    search_results = album_search(album_name)
    return [{"name": x["name"], "artist": x["artist"]} for x in search_results]

# GET: http://127.0.0.1:8000/albums
