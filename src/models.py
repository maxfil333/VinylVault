from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId  # id для Mongo


class VV_Album(BaseModel):
    album_id: str = Field(default_factory=lambda: str(ObjectId()))
    album_name: str
    artist_name: str
    cover_url: str = ''
    cover_url_reserve: str = ''
    order: int = 0  # Порядок альбома в коллекции пользователя


class VV_User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(ObjectId()))
    username: str
    password: str  # Хэшированный пароль
    email: EmailStr
    albums: list[VV_Album] = Field(default_factory=list)


class VV_Session(BaseModel):
    session_id: str
    username: str
    user_id: str
    login_time: datetime


class SearchResults(BaseModel):
    albums: list[VV_Album] = Field(default_factory=list)
    artist_top_albums: list[VV_Album] = Field(default_factory=list)


if __name__ == '__main__':
    user = VV_User(username='user', password='pass', email='abcd@gmail.com')
    print(user)

    album = VV_Album(album_name='album', artist_name='artist')
    print(album)

    user.albums.append(album)
    print(user)

    VV_User.model_validate(user.model_dump())  # валидация

    dct = {"username": "John", "password": "Doe", "email": "johndoe@gmail.com"}
    john = VV_User(**dct)  # from dict method 1
    print(john)
    john2  = VV_User.model_validate(dct) # from dict method 2
    print(john2)
