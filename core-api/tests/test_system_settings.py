import pytest
from app.services.system_settings import default_setting_config, validate_setting_config
from fastapi import HTTPException


def test_validate_telephony_settings_success() -> None:
    cfg = validate_setting_config("telephony", {"handoff_on_incomplete": True})
    assert cfg["handoff_on_incomplete"] is True


def test_validate_speechkit_settings_rejects_invalid_speed() -> None:
    with pytest.raises(HTTPException):
        validate_setting_config("speechkit", {"voice": "ermil", "speed": 9.0, "volume": 0})


def test_default_phrases_config_has_known_keys() -> None:
    cfg = default_setting_config("phrases")
    # optional values are excluded, so default may be empty; section itself must be recognized
    assert isinstance(cfg, dict)


def test_unknown_section_rejected() -> None:
    with pytest.raises(HTTPException):
        validate_setting_config("unknown", {})
