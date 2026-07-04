import asyncio
from typing import Optional
from datetime import datetime
from pymongo.results import InsertOneResult
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from src.models import VV_User, VV_Session
from utils.logger import logger


async def mongo_connect(host: str = "mongodb://localhost:27017/") -> AsyncIOMotorClient:
    """ Подключение к локальной базе данных MongoDB """
    logger.info("")
    client = AsyncIOMotorClient(host)
    return client


async def get_db(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    logger.info("")
    db = client[db_name]
    return db


# Глобальные переменные для клиента и базы данных
MONGO_CLIENT: Optional[AsyncIOMotorClient] = None
VINYL_VAULT_DB: Optional[AsyncIOMotorDatabase]  = None


async def init_database():
    """Инициализация подключения к MongoDB"""
    global MONGO_CLIENT, VINYL_VAULT_DB
    MONGO_CLIENT = await mongo_connect()

    try:
        await asyncio.wait_for(
            MONGO_CLIENT.admin.command("ping"),
            timeout=2.0,
        )
    except TimeoutError:
        logger.error(f"MongoDB недоступен")
        raise

    VINYL_VAULT_DB = await get_db(MONGO_CLIENT, 'VinylVault')
    logger.info("MongoDB подключение инициализировано")


async def close_database():
    """Закрытие подключения к MongoDB"""
    global MONGO_CLIENT
    if MONGO_CLIENT:
        MONGO_CLIENT.close()
        logger.info("MongoDB подключение закрыто")


async def add_user(collection: AsyncIOMotorCollection, user: VV_User) -> InsertOneResult:
    logger.info("")
    return await collection.insert_one(user.model_dump(by_alias=True))


async def add_session(collection: AsyncIOMotorCollection, session_id: str, user: VV_User) -> InsertOneResult:
    logger.info("")
    return await collection.insert_one(
        VV_Session(
            session_id=session_id,
            user_id=user.user_id,
            username=user.username,
            login_time=datetime.now()
        ).model_dump()
    )


async def is_in_collection(field: str, value: str, collection: AsyncIOMotorCollection) -> bool:
    logger.info("")
    return bool(await collection.find_one({field: value}))


async def _get_collection(db: AsyncIOMotorDatabase, collection_name: str) -> AsyncIOMotorCollection:
    logger.info("")
    collection = db[collection_name]
    return collection


async def get_users_collection() -> AsyncIOMotorCollection:
    logger.info("")
    if VINYL_VAULT_DB is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    return await _get_collection(VINYL_VAULT_DB, 'users_collection')


async def get_session_cookies_collection() -> AsyncIOMotorCollection:
    logger.info("")
    if VINYL_VAULT_DB is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database() сначала.")
    return await _get_collection(VINYL_VAULT_DB, 'session_cookies_collection')


if __name__ == "__main__":

    async def test():
        await init_database()
        users_collection = await _get_collection(VINYL_VAULT_DB, 'users_collection')
        session_cookies_collection = await _get_collection(VINYL_VAULT_DB, 'session_cookies_collection')

        await users_collection.drop()
        await session_cookies_collection.drop()

        u1 = await add_user(
            users_collection,
            VV_User(username='maxfil333', password='333', email="123asdasdx@mail.ru", user_id="testid")
        )
        u2 = await add_user(
            users_collection,
            VV_User(username='alice', password='123', email="123asdasdx@mail.ru")
        )
        print(u1.inserted_id)
        print(u2.inserted_id)

        # update
        await users_collection.update_one({"username": "alice"}, {"$set": {"password": "666"}})

        # get user by username and password
        collection = await get_users_collection()
        result = await collection.find_one({'username': 'maxfil333', 'password': '333'})
        print(result)

    asyncio.run(test())
