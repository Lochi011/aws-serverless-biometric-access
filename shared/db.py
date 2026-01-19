import os
import psycopg2
from psycopg2 import pool

from typing import Optional
_db_pool: Optional[pool.SimpleConnectionPool] = None


def _init_pool() -> pool.SimpleConnectionPool:
    return pool.SimpleConnectionPool(
        1, 10,
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=int(os.environ.get("DB_PORT", 5432)),
    )


def get_conn():
    global _db_pool
    if _db_pool is None:
        _db_pool = _init_pool()
    return _db_pool.getconn()


def put_conn(conn):
    if _db_pool:
        _db_pool.putconn(conn)
