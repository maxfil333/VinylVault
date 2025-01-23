from pymongo import MongoClient

from src.models import User


def mongo_connect(host: str = "mongodb://localhost:27017/"):
    """ Подключение к локальной базе данных MongoDB """
    client = MongoClient(host)
    return client


def get_db(client, db_name: str):
    db = client[db_name]
    return db


def get_collection(db, collection_name):
    collection = db[collection_name]
    return collection


def add_user(collection, user: User):
    return collection.insert_one(user.model_dump())


if __name__ == "__main__":
    client = mongo_connect()
    db = get_db(client, 'VinylVault')
    users_collection = get_collection(db, 'users_collection')

    users_collection.drop()

    u1 = add_user(users_collection, User(username='maxfil333', password='333'))
    u2 = add_user(users_collection, User(username='alice', password='123'))
    print(u1.inserted_id)
    print(u2.inserted_id)

    # update
    users_collection.update_one({"username": "alice"},
                                {"$set": {"password": "Valley 666 999 888"}})


