# Pain Data API

A FastAPI + SQL Server REST API to create, read, update and (soft) delete pain records,
with filtering, paging and a summary-statistics endpoint. Swagger UI is the client.

- **Stack:** Python 3.12, FastAPI, pyodbc, ODBC Driver 17 for SQL Server, SQL Server 2017+
- **Auth:** none. Intended for local use on `127.0.0.1` only.
- **SQL safety:** every value is a `?` parameter. Sort columns come from a fixed whitelist.

## Project layout

```
backend/
  app/
    main.py                     # app setup, /health, exception handlers
    config.py                   # settings from .env
    db.py                       # pyodbc connection per request
    schemas.py                  # Pydantic request/response models + validation
    errors.py                   # consistent JSON error envelope
    routers/pain.py             # HTTP endpoints
    services/pain_service.py    # business logic, commits, not-found handling
    repositories/pain_repo.py   # parameterized SQL
  sql/
    001_create_pain_records.sql # (re)creates dbo.PainRecords  -- DROPS the table
    seed_pain_records.sql       # optional sample data (41 records)
  .env.example
  requirements.txt
```

## Setup

Run all commands from the `backend` folder (PowerShell).

```powershell
# 1. Python environment
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# 2. Database: create the table. 001 DROPS dbo.PainRecords if it already exists.
sqlcmd -S PRITI_LAPTOP -U user1 -P "<password>" -i sql\001_create_pain_records.sql -v DB_NAME=HR_QA_DB

# Optional: 41 dummy records for testing (-f 65001 keeps accented names intact)
sqlcmd -S PRITI_LAPTOP -U user1 -P "<password>" -f 65001 -i sql\seed_pain_records.sql -v DB_NAME=HR_QA_DB

# 3. Config: copy the template and set DB_PASSWORD
Copy-Item .env.example .env
notepad .env

# 4. Run
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000/docs** to use Swagger UI. `http://127.0.0.1:8000/` redirects there.

The API connects to `PRITI_LAPTOP` / `HR_QA_DB` with SQL Server authentication (`user1`), using the settings in `.env`.

## Data model: `dbo.PainRecords`

| Column          | Type            | Rules                                          |
|-----------------|-----------------|------------------------------------------------|
| `id`            | INT IDENTITY    | Primary key                                    |
| `patient_name`  | NVARCHAR(200)   | Required, trimmed, 1–200 chars                 |
| `country`       | NVARCHAR(100)   | Required, trimmed, 1–100 chars (free text)     |
| `pain_level`    | TINYINT         | Required, integer 0–10 (`"5"` / `5.5` rejected)|
| `pain_location` | NVARCHAR(200)   | Required, trimmed, 1–200 chars                 |
| `occurred_at`   | DATETIME2 (UTC) | Required, ISO 8601, not in the future          |
| `notes`         | NVARCHAR(2000)  | Optional. Blank is stored as `null`            |
| `created_at`    | DATETIME2 (UTC) | Set by the database                            |
| `updated_at`    | DATETIME2 (UTC) | Set on every update or delete                  |
| `is_deleted`    | BIT             | Soft-delete flag, never exposed by the API     |

**Datetimes:** send ISO 8601. A value with an offset (`2026-09-30T14:30:00+05:30`) is converted to UTC.
A value without an offset is treated as UTC. All responses return UTC with a `Z` suffix.

Unknown JSON fields are rejected with 422.

## Endpoints

| Method | Path                         | Purpose                                     |
|--------|------------------------------|---------------------------------------------|
| GET    | `/health`                    | API + database connectivity check           |
| GET    | `/api/pain-records`          | List with filters, sorting, paging          |
| GET    | `/api/pain-records/stats`    | Summary KPIs (same filters as list)         |
| GET    | `/api/pain-records/{id}`     | Get one record                              |
| POST   | `/api/pain-records`          | Create (201 + `Location` header)            |
| PATCH  | `/api/pain-records/{id}`     | Partial update. Send only fields to change  |
| DELETE | `/api/pain-records/{id}`     | Soft delete. The record is hidden from all reads |

**List / stats query parameters** (all optional):

| Param            | Meaning                                              |
|------------------|------------------------------------------------------|
| `country`        | Exact match, case-insensitive                        |
| `pain_location`  | Exact match, case-insensitive                        |
| `patient_name`   | Contains, case-insensitive                           |
| `min_pain`, `max_pain` | Inclusive pain-level range (0–10)              |
| `occurred_from`, `occurred_to` | Inclusive ISO 8601 date range          |
| `page` (list)    | Default 1                                            |
| `page_size` (list) | Default 20, max 100                                |
| `sort_by` (list) | `occurred_at` (default), `id`, `pain_level`, `created_at`, `country`, `patient_name`, `pain_location` |
| `sort_dir` (list)| `desc` (default) or `asc`                            |

## Response format

Success:

```json
{ "success": true, "data": { "id": 1, "patient_name": "Jane Doe", "...": "..." } }
```

List (adds `meta`):

```json
{ "success": true, "data": [ ... ], "meta": { "page": 1, "page_size": 20, "total": 57, "total_pages": 3 } }
```

Stats:

```json
{
  "success": true,
  "data": {
    "total_records": 57,
    "pain_level": { "average": 5.84, "median": 6.0, "min": 0, "max": 10 },
    "occurred_at": { "earliest": "2026-01-03T08:00:00Z", "latest": "2026-09-29T21:10:00Z" }
  }
}
```

Error:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [ { "field": "pain_level", "message": "Input should be less than or equal to 10" } ]
  }
}
```

| HTTP | `error.code`             | When                                              |
|------|--------------------------|---------------------------------------------------|
| 422  | `VALIDATION_ERROR`       | Bad body, query or path value, or invalid JSON    |
| 404  | `NOT_FOUND`              | Unknown or soft-deleted record, or unknown route  |
| 405  | `METHOD_NOT_ALLOWED`     | Wrong HTTP method                                 |
| 503  | `DATABASE_UNAVAILABLE`   | SQL Server down or wrong credentials in `.env`    |
| 500  | `DATABASE_ERROR` / `INTERNAL_ERROR` | Unexpected. Details are logged server-side and not returned |

## Examples (PowerShell: use `curl.exe`, not the `curl` alias)

```powershell
# Create
curl.exe -X POST http://127.0.0.1:8000/api/pain-records -H "Content-Type: application/json" `
  -d '{\"patient_name\":\"Jane Doe\",\"country\":\"India\",\"pain_level\":6,\"pain_location\":\"Lower back\",\"occurred_at\":\"2026-09-29T08:15:00Z\"}'

# List: Indian records with pain >= 5, most severe first
curl.exe "http://127.0.0.1:8000/api/pain-records?country=India&min_pain=5&sort_by=pain_level"

# Stats for September 2026
curl.exe "http://127.0.0.1:8000/api/pain-records/stats?occurred_from=2026-09-01T00:00:00Z&occurred_to=2026-09-30T23:59:59Z"

# Partial update (clear notes, change pain level)
curl.exe -X PATCH http://127.0.0.1:8000/api/pain-records/1 -H "Content-Type: application/json" `
  -d '{\"pain_level\":4,\"notes\":null}'

# Soft delete
curl.exe -X DELETE http://127.0.0.1:8000/api/pain-records/1
```

## Restoring a soft-deleted record

The API does not expose restore. Run this with your Windows account:

```sql
UPDATE dbo.PainRecords SET is_deleted = 0, updated_at = SYSUTCDATETIME() WHERE id = <id>;
```
