import os
import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
        check_same_thread=False
    )
    conn.create_function("LOWER", 1, str.lower)
    conn.row_factory = sqlite3.Row
    

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn

@contextmanager
def get_connection():
    conn = _connect()
          
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
