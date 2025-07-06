from pymongo import MongoClient
from pymongo.results import InsertOneResult
from pymongo.collection import Collection
from pymongo.database import Database
import inspect

from src.models import VV_User


def mongo_connect(host: str = "mongodb://localhost:27017/") -> MongoClient:
    """ Подключение к локальной базе данных MongoDB """
    print("Function name:", inspect.currentframe().f_code.co_name)
    client = MongoClient(host)
    return client


MONGO_CLIENT = mongo_connect()


def get_db(client: MongoClient, db_name: str) -> Database:
    db = client[db_name]
    return db


VINYL_VAULT_DB = get_db(MONGO_CLIENT, 'VinylVault')


def get_collection(db: Database, collection_name) -> Collection:
    print("Function name:", inspect.currentframe().f_code.co_name)
    collection = db[collection_name]
    return collection


def add_user(collection: Collection, user: VV_User) -> InsertOneResult:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return collection.insert_one(user.model_dump(by_alias=True))


def is_in_collection(field: str, value: str, collection: Collection) -> bool:
    return True if collection.find_one({field: value}) else False


def vinyl_vault_users() -> Collection:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return get_collection(VINYL_VAULT_DB, 'users_collection')


if __name__ == "__main__":
    client = mongo_connect()
    db = get_db(client, 'VinylVault')
    users_collection = get_collection(db, 'users_collection')

    users_collection.drop()

    u1 = add_user(users_collection, VV_User(username='maxfil333', password='333', email="123asdasdx@mail.ru", user_id="testid"))
    u2 = add_user(users_collection, VV_User(username='alice', password='123', email="123asdasdx@mail.ru"))
    print(u1.inserted_id)
    print(u2.inserted_id)

    # update
    users_collection.update_one({"username": "alice"},
                                {"$set": {"password": "666"}})

    # get user by username and password
    print(vinyl_vault_users().find_one({'username': 'maxfil333', 'password': '333'}))
