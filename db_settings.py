import psycopg
from psycopg_pool import AsyncConnectionPool
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

class DBConnection:
    _pool: AsyncConnectionPool = None

    def __init__(self):
        raise RuntimeError('This is a singleton class! Invoke get_instance()')
    
    @classmethod
    async def create_pool(cls):
        if cls._pool is None:
            cls._pool = AsyncConnectionPool(conninfo=DATABASE_URL)
            await cls._pool.open()
            print("Async psycopg pool created.")
        return cls._pool

    @classmethod
    async def close_pool(cls):
        if cls._pool:
            await cls._pool.close()
            print("Async psycopg pool closed.")
