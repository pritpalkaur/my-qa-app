from datetime import datetime, timezone
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Field types
# ---------------------------------------------------------------------------

PatientName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Country = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PainLocation = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
# strict=True: 5 is accepted, but "5", 5.0 and true are not.
PainLevel = Annotated[int, Field(ge=0, le=10, strict=True)]

REQUIRED_FIELDS = ("patient_name", "country", "pain_level", "pain_location", "occurred_at")


def to_utc_naive(value: datetime) -> datetime:
    """Datetimes are stored as UTC without an offset. Naive input is treated as UTC."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _require_iso_string(value: Any) -> Any:
    if not isinstance(value, (str, datetime)):
        raise ValueError("must be an ISO 8601 datetime string, e.g. 2026-09-30T14:30:00Z")
    return value


def _normalize_occurred_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    value = to_utc_naive(value)
    if value > datetime.now(timezone.utc).replace(tzinfo=None):
        raise ValueError("must not be in the future")
    return value


def _blank_to_none(value: str | None) -> str | None:
    return value or None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class PainRecordCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "patient_name": "Jane Doe",
                "country": "India",
                "pain_level": 6,
                "pain_location": "Lower back",
                "occurred_at": "2026-09-29T08:15:00Z",
                "notes": "Worse after sitting for long periods.",
            }
        },
    )

    patient_name: PatientName
    country: Country
    pain_level: PainLevel
    pain_location: PainLocation
    occurred_at: datetime = Field(description="ISO 8601. Naive values are treated as UTC. Must not be in the future.")
    notes: Notes | None = None

    _check_occurred_at_type = field_validator("occurred_at", mode="before")(_require_iso_string)
    _check_occurred_at = field_validator("occurred_at")(_normalize_occurred_at)
    _check_notes = field_validator("notes")(_blank_to_none)


class PainRecordUpdate(BaseModel):
    """Partial update: only the fields sent are changed. Send "notes": null to clear notes."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"pain_level": 4, "notes": "Improving with physiotherapy."}},
    )

    patient_name: PatientName | None = None
    country: Country | None = None
    pain_level: PainLevel | None = None
    pain_location: PainLocation | None = None
    occurred_at: datetime | None = None
    notes: Notes | None = None

    _check_occurred_at_type = field_validator("occurred_at", mode="before")(
        lambda v: v if v is None else _require_iso_string(v)
    )
    _check_occurred_at = field_validator("occurred_at")(_normalize_occurred_at)
    _check_notes = field_validator("notes")(_blank_to_none)

    # Validators only run for fields that were actually sent, so this rejects explicit nulls only.
    @field_validator(*REQUIRED_FIELDS)
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("cannot be null")
        return value

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "PainRecordUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(include=self.model_fields_set)


SortField = Literal["id", "occurred_at", "pain_level", "created_at", "country", "patient_name", "pain_location"]


class PainFilters(BaseModel):
    country: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = Field(
        None, description="Exact match (case-insensitive)."
    )
    pain_location: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=200)] = Field(
        None, description="Exact match (case-insensitive)."
    )
    patient_name: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=200)] = Field(
        None, description="Contains match (case-insensitive)."
    )
    min_pain: int | None = Field(None, ge=0, le=10)
    max_pain: int | None = Field(None, ge=0, le=10)
    occurred_from: datetime | None = Field(None, description="Inclusive lower bound (ISO 8601).")
    occurred_to: datetime | None = Field(None, description="Inclusive upper bound (ISO 8601).")

    @field_validator("occurred_from", "occurred_to")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else to_utc_naive(value)

    @field_validator("country", "pain_location", "patient_name")
    @classmethod
    def _empty_is_none(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def _ranges(self) -> "PainFilters":
        if self.min_pain is not None and self.max_pain is not None and self.min_pain > self.max_pain:
            raise ValueError("min_pain must be less than or equal to max_pain")
        if self.occurred_from and self.occurred_to and self.occurred_from > self.occurred_to:
            raise ValueError("occurred_from must be earlier than or equal to occurred_to")
        return self


class ListParams(PainFilters):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: SortField = "occurred_at"
    sort_dir: Literal["asc", "desc"] = "desc"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class _UtcModel(BaseModel):
    """Datetimes come back from SQL Server as naive UTC; mark them so JSON output ends in 'Z'."""

    @field_validator("*")
    @classmethod
    def _mark_utc(cls, value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class PainRecord(_UtcModel):
    id: int
    patient_name: str
    country: str
    pain_level: int
    pain_location: str
    occurred_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime | None


class PainLevelStats(BaseModel):
    average: float | None
    median: float | None
    min: int | None
    max: int | None


class DateRange(_UtcModel):
    earliest: datetime | None
    latest: datetime | None


class PainStats(BaseModel):
    total_records: int
    pain_level: PainLevelStats
    occurred_at: DateRange


class DeletedRecord(BaseModel):
    id: int
    deleted: bool = True


class HealthStatus(BaseModel):
    status: str
    database: str


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PagedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PageMeta


class ErrorDetail(BaseModel):
    field: str | None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorBody
