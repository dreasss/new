from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError


class TelephonySettingsConfig(BaseModel):
    handoff_on_incomplete: bool = False


class SpeechKitSettingsConfig(BaseModel):
    voice: str = Field(default="ermil", min_length=1, max_length=64)
    speed: float = Field(default=1.0, ge=0.1, le=3.0)
    volume: int = Field(default=0, ge=-100, le=100)


class BrandingSettingsConfig(BaseModel):
    title: str = Field(default="Support Portal", min_length=1, max_length=128)
    primaryColor: str = Field(default="#2563eb", min_length=4, max_length=32)


class PhraseSettingsConfig(BaseModel):
    GREETING: str | None = Field(default=None, min_length=1, max_length=300)
    FIO: str | None = Field(default=None, min_length=1, max_length=300)
    DEPARTMENT: str | None = Field(default=None, min_length=1, max_length=300)
    CABINET: str | None = Field(default=None, min_length=1, max_length=300)
    PROBLEM: str | None = Field(default=None, min_length=1, max_length=300)
    EXTRA: str | None = Field(default=None, min_length=1, max_length=300)
    CONFIRM: str | None = Field(default=None, min_length=1, max_length=300)
    INCOMPLETE: str | None = Field(default=None, min_length=1, max_length=300)
    COMPLETE: str | None = Field(default=None, min_length=1, max_length=300)


class SSOSettingsConfig(BaseModel):
    provider: str | None = Field(default=None, max_length=16)
    enabled: bool = False


SECTION_MODELS: dict[str, type[BaseModel]] = {
    "telephony": TelephonySettingsConfig,
    "speechkit": SpeechKitSettingsConfig,
    "branding": BrandingSettingsConfig,
    "phrases": PhraseSettingsConfig,
    "sso": SSOSettingsConfig,
}


def validate_setting_config(section: str, config: dict[str, Any]) -> dict[str, Any]:
    model = SECTION_MODELS.get(section)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown settings section: {section}")
    try:
        parsed = model.model_validate(config)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return parsed.model_dump(exclude_none=True)


def default_setting_config(section: str) -> dict[str, Any]:
    model = SECTION_MODELS.get(section)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown settings section: {section}")
    return model().model_dump(exclude_none=True)
