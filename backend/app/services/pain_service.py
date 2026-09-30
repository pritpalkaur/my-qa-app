import math

import pyodbc

from app.errors import NotFoundError
from app.repositories import pain_repo
from app.schemas import (
    DateRange,
    ListParams,
    PageMeta,
    PainFilters,
    PainLevelStats,
    PainRecord,
    PainRecordCreate,
    PainRecordUpdate,
    PainStats,
)


def _not_found(record_id: int) -> NotFoundError:
    return NotFoundError(f"Pain record {record_id} was not found")


def list_records(conn: pyodbc.Connection, params: ListParams) -> tuple[list[PainRecord], PageMeta]:
    rows, total = pain_repo.list_records(
        conn,
        params,
        page=params.page,
        page_size=params.page_size,
        sort_by=params.sort_by,
        sort_dir=params.sort_dir,
    )
    meta = PageMeta(
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=math.ceil(total / params.page_size),
    )
    return [PainRecord(**row) for row in rows], meta


def get_record(conn: pyodbc.Connection, record_id: int) -> PainRecord:
    row = pain_repo.get_record(conn, record_id)
    if row is None:
        raise _not_found(record_id)
    return PainRecord(**row)


def create_record(conn: pyodbc.Connection, payload: PainRecordCreate) -> PainRecord:
    row = pain_repo.insert_record(conn, payload.model_dump())
    conn.commit()
    return PainRecord(**row)


def update_record(conn: pyodbc.Connection, record_id: int, payload: PainRecordUpdate) -> PainRecord:
    row = pain_repo.update_record(conn, record_id, payload.changes())
    if row is None:
        raise _not_found(record_id)
    conn.commit()
    return PainRecord(**row)


def delete_record(conn: pyodbc.Connection, record_id: int) -> None:
    if not pain_repo.soft_delete_record(conn, record_id):
        raise _not_found(record_id)
    conn.commit()


def get_stats(conn: pyodbc.Connection, filters: PainFilters) -> PainStats:
    row = pain_repo.get_stats(conn, filters)
    average = row["avg_pain"]
    median = row["median_pain"]
    return PainStats(
        total_records=row["total_records"],
        pain_level=PainLevelStats(
            average=None if average is None else round(float(average), 2),
            median=None if median is None else round(float(median), 2),
            min=row["min_pain"],
            max=row["max_pain"],
        ),
        occurred_at=DateRange(earliest=row["earliest"], latest=row["latest"]),
    )
