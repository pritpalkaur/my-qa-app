import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.db import connect
from app.errors import register_exception_handlers
from app.repositories import pain_repo
from app.routers import pain
from app.schemas import ApiResponse, ErrorResponse, HealthStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Pain Data API",
    version="1.0.0",
    description=(
        "CRUD API for pain records stored in SQL Server.\n\n"
        "Every response uses the same envelope: `{success, data, meta?}` on success, "
        "`{success: false, error: {code, message, details}}` on failure. "
        "Datetimes are UTC (ISO 8601)."
    ),
)

register_exception_handlers(app)
app.include_router(pain.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=ApiResponse[HealthStatus],
    responses={503: {"model": ErrorResponse}},
    tags=["Health"],
    summary="API and database health",
)
def health():
    conn = connect()
    try:
        pain_repo.ping(conn)
    finally:
        conn.close()
    return ApiResponse[HealthStatus](data=HealthStatus(status="ok", database="up"))
