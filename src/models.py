from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId  # id для Mongo


class Album(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")  # alias для Mongo
    name: str
    artist: str
    image: list


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    username: str
    password: str  # Хэшированный пароль
    email: EmailStr
    albums: list[Album] = []


if __name__ == '__main__':
    user = User(username='user', password='pass')
    print(user)

    album = Album(name='album', artist='artist', image=[])
    print(album)

    user.albums.append(album)
    print(user)

    User.model_validate(user.model_dump())  # валидация
