"""Data access for dbo.PainRecords.

Every value goes through a `?` parameter. The only SQL built dynamically is column names,
and those come from fixed whitelists (SORT_COLUMNS, UPDATABLE_COLUMNS), never from user text.
"""

from typing import Any

import pyodbc

from app.schemas import PainFilters

SELECT_COLUMNS = "id, patient_name, country, pain_level, pain_location, occurred_at, notes, created_at, updated_at"
INSERTED_COLUMNS = ", ".join(f"INSERTED.{c.strip()}" for c in SELECT_COLUMNS.split(","))

SORT_COLUMNS = {
    "id": "id",
    "occurred_at": "occurred_at",
    "pain_level": "pain_level",
    "created_at": "created_at",
    "country": "country",
    "patient_name": "patient_name",
    "pain_location": "pain_location",
}
UPDATABLE_COLUMNS = {"patient_name", "country", "pain_level", "pain_location", "occurred_at", "notes"}


def _rows_to_dicts(cursor: pyodbc.Cursor, rows: list[pyodbc.Row]) -> list[dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def _fetch_one(cursor: pyodbc.Cursor) -> dict[str, Any] | None:
    row = cursor.fetchone()
    return None if row is None else _rows_to_dicts(cursor, [row])[0]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("[", "\\[")


def _where(filters: PainFilters) -> tuple[str, list[Any]]:
    clauses = ["is_deleted = 0"]
    params: list[Any] = []
    if filters.country:
        clauses.append("country = ?")
        params.append(filters.country)
    if filters.pain_location:
        clauses.append("pain_location = ?")
        params.append(filters.pain_location)
    if filters.patient_name:
        clauses.append("patient_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(filters.patient_name)}%")
    if filters.min_pain is not None:
        clauses.append("pain_level >= ?")
        params.append(filters.min_pain)
    if filters.max_pain is not None:
        clauses.append("pain_level <= ?")
        params.append(filters.max_pain)
    if filters.occurred_from is not None:
        clauses.append("occurred_at >= ?")
        params.append(filters.occurred_from)
    if filters.occurred_to is not None:
        clauses.append("occurred_at <= ?")
        params.append(filters.occurred_to)
    return " AND ".join(clauses), params


def list_records(
    conn: pyodbc.Connection,
    filters: PainFilters,
    *,
    page: int,
    page_size: int,
    sort_by: str,
    sort_dir: str,
) -> tuple[list[dict[str, Any]], int]:
    where, params = _where(filters)
    sort_column = SORT_COLUMNS[sort_by]
    direction = "ASC" if sort_dir == "asc" else "DESC"

    cursor = conn.cursor()
    total = cursor.execute(f"SELECT COUNT(*) FROM dbo.PainRecords WHERE {where}", params).fetchval()

    cursor.execute(
        f"SELECT {SELECT_COLUMNS} FROM dbo.PainRecords WHERE {where} "
        f"ORDER BY {sort_column} {direction}, id {direction} "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        [*params, (page - 1) * page_size, page_size],
    )
    return _rows_to_dicts(cursor, cursor.fetchall()), total


def get_record(conn: pyodbc.Connection, record_id: int) -> dict[str, Any] | None:
    cursor = conn.cursor()
    cursor.execute(f"SELECT {SELECT_COLUMNS} FROM dbo.PainRecords WHERE id = ? AND is_deleted = 0", record_id)
    return _fetch_one(cursor)


def insert_record(conn: pyodbc.Connection, values: dict[str, Any]) -> dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dbo.PainRecords (patient_name, country, pain_level, pain_location, occurred_at, notes) "
        f"OUTPUT {INSERTED_COLUMNS} "
        "VALUES (?, ?, ?, ?, ?, ?)",
        values["patient_name"],
        values["country"],
        values["pain_level"],
        values["pain_location"],
        values["occurred_at"],
        values.get("notes"),
    )
    return _fetch_one(cursor)


def update_record(conn: pyodbc.Connection, record_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
    columns = [c for c in changes if c in UPDATABLE_COLUMNS]
    assignments = ", ".join(f"{c} = ?" for c in columns)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE dbo.PainRecords SET {assignments}, updated_at = SYSUTCDATETIME() "
        f"OUTPUT {INSERTED_COLUMNS} "
        "WHERE id = ? AND is_deleted = 0",
        [*(changes[c] for c in columns), record_id],
    )
    return _fetch_one(cursor)


def soft_delete_record(conn: pyodbc.Connection, record_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE dbo.PainRecords SET is_deleted = 1, updated_at = SYSUTCDATETIME() WHERE id = ? AND is_deleted = 0",
        record_id,
    )
    return cursor.rowcount == 1


def get_stats(conn: pyodbc.Connection, filters: PainFilters) -> dict[str, Any]:
    where, params = _where(filters)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS total_records, "
        "       AVG(CAST(pain_level AS DECIMAL(5, 2))) AS avg_pain, "
        "       MIN(pain_level) AS min_pain, "
        "       MAX(pain_level) AS max_pain, "
        "       MIN(occurred_at) AS earliest, "
        "       MAX(occurred_at) AS latest "
        f"FROM dbo.PainRecords WHERE {where}",
        params,
    )
    stats = _fetch_one(cursor)

    # PERCENTILE_CONT is a window function in SQL Server; every row carries the same value.
    stats["median_pain"] = cursor.execute(
        "SELECT TOP (1) PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pain_level) OVER () "
        f"FROM dbo.PainRecords WHERE {where}",
        params,
    ).fetchval()
    return stats


def ping(conn: pyodbc.Connection) -> None:
    conn.cursor().execute("SELECT 1").fetchval()
