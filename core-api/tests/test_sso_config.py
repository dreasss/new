import pytest
from app.services.sso import validate_oidc_config, validate_saml_config
from fastapi import HTTPException


def test_validate_oidc_config_requires_fields() -> None:
    with pytest.raises(HTTPException):
        validate_oidc_config({"issuer": "x"})


def test_validate_saml_config_accepts_metadata_mode() -> None:
    validate_saml_config(
        {
            "metadata_xml": "<xml></xml>",
            "sp_entity_id": "sp",
            "acs_url": "http://localhost/callback",
        }
    )
