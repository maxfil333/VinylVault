import asyncio
import inspect
from datetime import datetime
from pymongo.results import InsertOneResult
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from src.models import VV_User, VV_Session


async def mongo_connect(host: str = "mongodb://localhost:27017/") -> AsyncIOMotorClient:
    """ Подключение к локальной базе данных MongoDB """
    print("Function name:", inspect.currentframe().f_code.co_name)
    client = AsyncIOMotorClient(host)
    return client


async def get_db(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    db = client[db_name]
    return db


# Создаем константы для клиента и базы данных
MONGO_CLIENT = asyncio.get_event_loop().run_until_complete(mongo_connect())
VINYL_VAULT_DB = asyncio.get_event_loop().run_until_complete(get_db(MONGO_CLIENT, 'VinylVault'))


async def get_collection(db: AsyncIOMotorDatabase, collection_name: str) -> AsyncIOMotorCollection:
    print("Function name:", inspect.currentframe().f_code.co_name)
    collection = db[collection_name]
    return collection


async def add_user(collection: AsyncIOMotorCollection, user: VV_User) -> InsertOneResult:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return await collection.insert_one(user.model_dump(by_alias=True))


async def add_session(collection: AsyncIOMotorCollection, session_id: str, username: str) -> InsertOneResult:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return await collection.insert_one(
        VV_Session(
            session_id=session_id,
            username=username,
            login_time=datetime.now()
        ).model_dump()
    )


async def is_in_collection(field: str, value: str, collection: AsyncIOMotorCollection) -> bool:
    return bool(await collection.find_one({field: value}))


async def vinyl_vault_users() -> AsyncIOMotorCollection:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return await get_collection(VINYL_VAULT_DB, 'users_collection')


async def session_cookies() -> AsyncIOMotorCollection:
    print("Function name:", inspect.currentframe().f_code.co_name)
    return await get_collection(VINYL_VAULT_DB, 'session_cookies_collection')


async def main():
    users_collection = await get_collection(VINYL_VAULT_DB, 'users_collection')
    session_cookies_collection = await get_collection(VINYL_VAULT_DB, 'session_cookies_collection')

    await users_collection.drop()
    await session_cookies_collection.drop()

    u1 = await add_user(users_collection, VV_User(username='maxfil333', password='333', email="123asdasdx@mail.ru", user_id="testid"))
    u2 = await add_user(users_collection, VV_User(username='alice', password='123', email="123asdasdx@mail.ru"))
    print(u1.inserted_id)
    print(u2.inserted_id)

    # update
    await users_collection.update_one({"username": "alice"}, {"$set": {"password": "666"}})

    # get user by username and password
    collection = await vinyl_vault_users()
    result = await collection.find_one({'username': 'maxfil333', 'password': '333'})
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
