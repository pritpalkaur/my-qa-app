from collections.abc import Iterator

import pyodbc

from app.config import get_settings

# ODBC driver-manager connection pooling (on by default; set explicitly for clarity).
pyodbc.pooling = True


def connect() -> pyodbc.Connection:
    settings = get_settings()
    return pyodbc.connect(
        settings.connection_string,
        timeout=settings.db_timeout_seconds,
        autocommit=False,
    )


def get_db() -> Iterator[pyodbc.Connection]:
    """FastAPI dependency: one connection per request. Services commit their own writes."""
    conn = connect()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
