import sqlite3
from contextlib import contextmanager

from app import config
from app.database.models import SCHEMA


@contextmanager
def connect():
    """Open a short-lived connection (safe across FastAPI worker threads)."""
    conn = sqlite3.connect(str(config.db_path()), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
