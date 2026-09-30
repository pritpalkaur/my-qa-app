from typing import Annotated

import pyodbc
from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.db import get_db
from app.schemas import (
    ApiResponse,
    DeletedRecord,
    ErrorResponse,
    ListParams,
    PagedResponse,
    PainFilters,
    PainRecord,
    PainRecordCreate,
    PainRecordUpdate,
    PainStats,
)
from app.services import pain_service

router = APIRouter(
    prefix="/api/pain-records",
    tags=["Pain records"],
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server or database error"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)

Conn = Annotated[pyodbc.Connection, Depends(get_db)]
RecordId = Annotated[int, Path(ge=1, description="Pain record id")]
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Record not found"}}


@router.get("", response_model=PagedResponse[PainRecord], summary="List pain records")
def list_pain_records(conn: Conn, params: Annotated[ListParams, Query()]):
    """Filter, sort and page through records. Soft-deleted records are never returned."""
    records, meta = pain_service.list_records(conn, params)
    return PagedResponse[PainRecord](data=records, meta=meta)


@router.get("/stats", response_model=ApiResponse[PainStats], summary="Summary statistics")
def get_pain_stats(conn: Conn, filters: Annotated[PainFilters, Query()]):
    """Overall KPIs: record count, average / median / min / max pain level and the date range.
    Accepts the same filters as the list endpoint."""
    return ApiResponse[PainStats](data=pain_service.get_stats(conn, filters))


@router.get("/{record_id}", response_model=ApiResponse[PainRecord], responses=NOT_FOUND, summary="Get a pain record")
def get_pain_record(conn: Conn, record_id: RecordId):
    return ApiResponse[PainRecord](data=pain_service.get_record(conn, record_id))


@router.post(
    "",
    response_model=ApiResponse[PainRecord],
    status_code=status.HTTP_201_CREATED,
    summary="Create a pain record",
)
def create_pain_record(conn: Conn, payload: PainRecordCreate, response: Response):
    record = pain_service.create_record(conn, payload)
    response.headers["Location"] = f"{router.prefix}/{record.id}"
    return ApiResponse[PainRecord](data=record)


@router.patch(
    "/{record_id}",
    response_model=ApiResponse[PainRecord],
    responses=NOT_FOUND,
    summary="Update a pain record (partial)",
)
def update_pain_record(conn: Conn, record_id: RecordId, payload: PainRecordUpdate):
    """Send only the fields to change. `"notes": null` clears notes; other fields cannot be null."""
    return ApiResponse[PainRecord](data=pain_service.update_record(conn, record_id, payload))


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[DeletedRecord],
    responses=NOT_FOUND,
    summary="Delete a pain record (soft delete)",
)
def delete_pain_record(conn: Conn, record_id: RecordId):
    """Marks the record as deleted. It disappears from all reads but stays in the database."""
    pain_service.delete_record(conn, record_id)
    return ApiResponse[DeletedRecord](data=DeletedRecord(id=record_id))
