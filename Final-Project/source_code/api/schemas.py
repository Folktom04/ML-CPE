"""Pydantic request/response models for the UV Guard API (day 16).

Every response carries ``disclaimer`` (estimates for education and warning, not a diagnosis).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.risk import DISCLAIMER, normalize_skin_type


class Disclaimed(BaseModel):
    """Base for every response: always includes the Thai disclaimer."""

    disclaimer: str = DISCLAIMER


def _skin_value(v: object) -> str:
    """Normalise I-VI or 1-6 to the Roman numeral (ValueError for anything else)."""
    return normalize_skin_type(int(v) if str(v).isdigit() else str(v))


class PredictRequest(BaseModel):
    """Body of ``POST /predict``."""

    lat: float = Field(ge=-90, le=90, description="Latitude (degrees)")
    lon: float = Field(ge=-180, le=180, description="Longitude (degrees)")
    skin_type: str = Field(description="Fitzpatrick type I-VI (or 1-6)")

    @field_validator("skin_type", mode="before")
    @classmethod
    def _skin(cls, v: object) -> str:
        """Accept I-VI or 1-6 and store the Roman numeral."""
        return _skin_value(v)


class HourUV(BaseModel):
    """One forecast hour (``time`` = local start of the hour, Asia/Bangkok)."""

    time: str
    uvi: float
    uvi_range: list[float] = Field(min_length=2, max_length=2)
    uva_wm2: float
    uvb_wm2: float
    level: str
    interval_adjusted: bool
    data_imputed: bool = Field(False, description="some Open-Meteo input was missing and filled")


class PredictResponse(Disclaimed):
    """Response of ``POST /predict`` (fields required by the project rules come first)."""

    uvi: float
    uvi_range: list[float] = Field(min_length=2, max_length=2)
    uva_wm2: float
    uvb_wm2: float
    level: str
    skin_type: str
    burn_minutes: int | None
    cmf: float | None
    advice: list[str]
    forecast: list[HourUV]
    next_safe_time: str | None
    time: str
    is_daylight: bool
    level_en: str
    level_color: str
    uvi_q90_cqr: float = Field(description="upper quantile q90 after CQR")
    alert_uvi: float = Field(description="max(q90 after CQR, uvi); drives alerts, burn, advice")
    alert_level: str
    interval_adjusted: bool = Field(description="point UVI was outside [q10, q90]; range widened")
    data_imputed: bool = Field(description="some Open-Meteo input of this hour was filled")
    note: str | None = None


class ForecastResponse(Disclaimed):
    """Response of ``GET /forecast``."""

    lat: float
    lon: float
    hours: list[HourUV]
    note: str | None = None


class SkyImageResponse(Disclaimed):
    """Response of ``POST /sky-image`` (supporting information only, never changes the UVI)."""

    sky_class: str = Field(description="SWIMCAT-ext class (6 classes); the main result")
    sky_class_th: str
    sky_confidence: float = Field(ge=0, le=1, description="softmax probability of sky_class")
    sky_class_probs: dict[str, float]
    cloud_fraction_rb: float
    cloud_fraction_cnn: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="cloud fraction IN THE IMAGE from the SWIMSEG head (not the whole sky); "
        "sent only while that head's test result passes its criteria",
    )
    reliability: dict[str, str]
    note: str
    stored: bool = False


class HealthResponse(Disclaimed):
    """Response of ``GET /health``."""

    status: str
    models: dict[str, str]
    sky_backend: str
    cqr_q: float
    db_backend: str = Field(description="postgresql (target) or sqlite (fallback only)")
    db_fallback: bool = Field(description="true when DATABASE_URL is unset and SQLite is used")
    db_ok: bool = Field(description="database answered SELECT 1")


class ErrorResponse(Disclaimed):
    """Error body (validation errors, upstream failures)."""

    detail: object


class UserSettingsUpdate(BaseModel):
    """Body of ``PUT /users/{id}/settings`` (only the fields sent are changed).

    ``safe_threshold`` is not accepted: the server derives it as ``alert_threshold - 2``.
    """

    model_config = ConfigDict(extra="forbid")

    skin_type: str | None = Field(None, description="Fitzpatrick type I-VI (or 1-6)")
    notify_enabled: bool | None = None
    alert_threshold: float | None = Field(None, ge=3, le=11, description="alert at UVI >= this")
    alert_burn_minutes: int | None = Field(None, ge=5, le=240)
    province: str | None = Field(None, max_length=64)

    @field_validator("skin_type", mode="before")
    @classmethod
    def _skin(cls, v: object) -> str | None:
        """Accept I-VI or 1-6 (or nothing)."""
        return None if v is None else _skin_value(v)


class UserCreate(UserSettingsUpdate):
    """Body of ``POST /users``; the device id goes in the ``X-Device-Id`` header."""

    skin_type: str = Field(description="Fitzpatrick type I-VI (or 1-6)")


class UserResponse(Disclaimed):
    """A user's settings (the device id is never returned)."""

    id: int
    skin_type: str
    province: str | None
    notify_enabled: bool
    alert_threshold: float
    safe_threshold: float = Field(description="'safe again' UVI = alert_threshold - 2")
    alert_burn_minutes: int
    updated_at: str = Field(description="UTC, ISO 8601")
