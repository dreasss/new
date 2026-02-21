import json
import os
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import jwt
import requests
from app.models import SSOProviderConfig, SSOProviderType, User, UserRole
from app.services.auth import create_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt
from fastapi import HTTPException, Request
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from sqlalchemy.orm import Session

SSO_STATE_SECRET = os.getenv("SSO_STATE_SECRET", os.getenv("JWT_SECRET", "dev-secret"))
SSO_ENABLED = os.getenv("SSO_ENABLED", "false").lower() == "true"


class SSOProviderAdapter(ABC):
    @abstractmethod
    async def get_login_redirect(self, request: Request, config: dict) -> str:
        pass

    @abstractmethod
    async def handle_callback(self, request: Request, config: dict) -> dict:
        pass

    @abstractmethod
    def get_or_create_user(self, db: Session, identity: dict) -> User:
        pass


class OIDCProviderAdapter(SSOProviderAdapter):
    async def get_login_redirect(self, request: Request, config: dict) -> str:
        validate_oidc_config(config)
        metadata = requests.get(f"{config['issuer'].rstrip('/')}/.well-known/openid-configuration", timeout=10).json()
        state = _build_state_token({"provider": "OIDC", "nonce": secrets.token_urlsafe(16)})
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": config.get("scope", "openid profile email"),
            "state": state,
        }
        return f"{metadata['authorization_endpoint']}?{urlencode(params)}"

    async def handle_callback(self, request: Request, config: dict) -> dict:
        validate_oidc_config(config)
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state or not code:
            raise HTTPException(status_code=400, detail="Missing OIDC callback params")

        _decode_state_token(state)
        metadata = requests.get(f"{config['issuer'].rstrip('/')}/.well-known/openid-configuration", timeout=10).json()
        client = AsyncOAuth2Client(client_id=config["client_id"], client_secret=config["client_secret"])
        token = await client.fetch_token(
            metadata["token_endpoint"],
            grant_type="authorization_code",
            code=code,
            redirect_uri=config["redirect_uri"],
        )
        if "id_token" not in token:
            raise HTTPException(status_code=400, detail="OIDC token response missing id_token")

        jwks = requests.get(metadata["jwks_uri"], timeout=10).json()
        claims = authlib_jwt.decode(token["id_token"], JsonWebKey.import_key_set(jwks))
        claims.validate()

        subject = claims.get("sub")
        email = claims.get("email")
        if not subject or not email:
            raise HTTPException(status_code=400, detail="OIDC claims missing sub/email")
        return {"subject": subject, "email": email}

    def get_or_create_user(self, db: Session, identity: dict) -> User:
        user = db.query(User).filter(User.sso_subject == identity["subject"]).first()
        if user:
            return user
        by_email = db.query(User).filter(User.email == identity["email"]).first()
        if by_email:
            by_email.sso_subject = identity["subject"]
            db.add(by_email)
            db.commit()
            db.refresh(by_email)
            return by_email

        user = User(
            email=identity["email"],
            sso_subject=identity["subject"],
            role=UserRole.USER,
            password_hash="!sso-account!",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


class SAMLProviderAdapter(SSOProviderAdapter):
    async def get_login_redirect(self, request: Request, config: dict) -> str:
        settings = _build_saml_settings(config)
        req = _prepare_saml_req(request)
        auth = OneLogin_Saml2_Auth(req, settings)
        return auth.login()

    async def handle_callback(self, request: Request, config: dict) -> dict:
        settings = _build_saml_settings(config)
        req = _prepare_saml_req(request)
        auth = OneLogin_Saml2_Auth(req, settings)
        auth.process_response()
        errors = auth.get_errors()
        if errors:
            raise HTTPException(status_code=400, detail=f"SAML validation failed: {','.join(errors)}")
        if not auth.is_authenticated():
            raise HTTPException(status_code=401, detail="SAML user not authenticated")

        subject = auth.get_nameid()
        attrs = auth.get_attributes()
        email = None
        for key in ["email", "Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"]:
            values = attrs.get(key)
            if values:
                email = values[0]
                break
        if not subject or not email:
            raise HTTPException(status_code=400, detail="SAML assertion missing subject/email")
        return {"subject": subject, "email": email}

    def get_or_create_user(self, db: Session, identity: dict) -> User:
        return OIDCProviderAdapter().get_or_create_user(db, identity)


def _prepare_saml_req(request: Request) -> dict:
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.url.hostname,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": {},
    }


def _build_saml_settings(config: dict) -> dict:
    validate_saml_config(config)
    if config.get("metadata_xml"):
        parsed = OneLogin_Saml2_IdPMetadataParser.parse(config["metadata_xml"])
        parsed["sp"] = {
            "entityId": config["sp_entity_id"],
            "assertionConsumerService": {
                "url": config["acs_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": config.get("sp_x509cert", ""),
            "privateKey": config.get("sp_private_key", ""),
        }
        return parsed

    return {
        "strict": True,
        "debug": False,
        "sp": {
            "entityId": config["sp_entity_id"],
            "assertionConsumerService": {
                "url": config["acs_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": config.get("sp_x509cert", ""),
            "privateKey": config.get("sp_private_key", ""),
        },
        "idp": {
            "entityId": config["idp_entity_id"],
            "singleSignOnService": {
                "url": config["idp_sso_url"],
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": config["idp_x509cert"],
        },
    }


def _build_state_token(payload: dict) -> str:
    now = datetime.now(UTC)
    data = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(data, SSO_STATE_SECRET, algorithm="HS256")


def _decode_state_token(token: str) -> dict:
    try:
        return jwt.decode(token, SSO_STATE_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid SSO state: {exc}") from exc


def validate_oidc_config(config: dict) -> None:
    required = ["issuer", "client_id", "client_secret", "redirect_uri"]
    for field in required:
        if not config.get(field):
            raise HTTPException(status_code=500, detail=f"OIDC misconfigured: missing {field}")


def validate_saml_config(config: dict) -> None:
    if config.get("metadata_xml"):
        for field in ["sp_entity_id", "acs_url"]:
            if not config.get(field):
                raise HTTPException(status_code=500, detail=f"SAML misconfigured: missing {field}")
        return
    required = ["sp_entity_id", "acs_url", "idp_entity_id", "idp_sso_url", "idp_x509cert"]
    for field in required:
        if not config.get(field):
            raise HTTPException(status_code=500, detail=f"SAML misconfigured: missing {field}")


def load_active_sso_config(db: Session) -> tuple[str, dict] | None:
    row = db.query(SSOProviderConfig).filter(SSOProviderConfig.enabled.is_(True)).first()
    if row:
        return row.provider_type.value, json.loads(row.config_json)

    provider = os.getenv("SSO_PROVIDER", "")
    if not provider:
        return None
    if provider == "OIDC":
        cfg = {
            "issuer": os.getenv("OIDC_ISSUER"),
            "client_id": os.getenv("OIDC_CLIENT_ID"),
            "client_secret": os.getenv("OIDC_CLIENT_SECRET"),
            "redirect_uri": os.getenv("OIDC_REDIRECT_URI"),
            "scope": os.getenv("OIDC_SCOPE", "openid profile email"),
        }
        validate_oidc_config(cfg)
        return "OIDC", cfg
    if provider == "SAML":
        cfg = {
            "metadata_xml": os.getenv("SAML_METADATA_XML"),
            "sp_entity_id": os.getenv("SAML_SP_ENTITY_ID"),
            "acs_url": os.getenv("SAML_ACS_URL"),
            "sp_x509cert": os.getenv("SAML_SP_X509CERT", ""),
            "sp_private_key": os.getenv("SAML_SP_PRIVATE_KEY", ""),
            "idp_entity_id": os.getenv("SAML_IDP_ENTITY_ID"),
            "idp_sso_url": os.getenv("SAML_IDP_SSO_URL"),
            "idp_x509cert": os.getenv("SAML_IDP_X509CERT"),
        }
        validate_saml_config(cfg)
        return "SAML", cfg
    raise HTTPException(status_code=500, detail="Unsupported SSO_PROVIDER")


def get_adapter(provider_type: str) -> SSOProviderAdapter:
    if provider_type == SSOProviderType.OIDC.value:
        return OIDCProviderAdapter()
    if provider_type == SSOProviderType.SAML.value:
        return SAMLProviderAdapter()
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider_type}")


def maybe_validate_sso_startup(db: Session) -> None:
    if not SSO_ENABLED:
        return
    conf = load_active_sso_config(db)
    if not conf:
        raise RuntimeError("SSO_ENABLED=true but no SSO configuration found")


def complete_sso_login(db: Session, provider_type: str, identity: dict) -> str:
    adapter = get_adapter(provider_type)
    user = adapter.get_or_create_user(db, identity)
    return create_token(user)
