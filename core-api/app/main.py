import json
import logging
import os
import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, engine, get_db
from app.models import (
    CallLog,
    SSOProviderConfig,
    SSOProviderType,
    SystemSetting,
    Ticket,
    TicketComment,
    TicketHistory,
    TicketRating,
    TicketStatus,
    User,
    UserRole,
)
from app.schemas import (
    LoginRequest,
    SpeakerEnrollRequest,
    SpeakerEnrollResponse,
    SpeakerIdentifyRequest,
    SpeakerIdentifyResponse,
    SSOConfigResponse,
    SSOConfigUpsertRequest,
    SystemSettingRequest,
    SystemSettingResponse,
    TicketAssignRequest,
    TicketCloseRequest,
    TicketCommentRequest,
    TicketCreatePortalRequest,
    TicketHistoryResponse,
    TicketRatingRequest,
    TicketStatusRequest,
    TokenResponse,
)
from app.services.auth import create_token, get_current_user, hash_password, verify_password
from app.services.speaker import LocalSpeakerRecognizer
from app.services.sso import (
    complete_sso_login,
    get_adapter,
    load_active_sso_config,
    maybe_validate_sso_startup,
    validate_oidc_config,
    validate_saml_config,
)
# codex/define-architecture-for-support-system-e3u2rv
from app.services.system_settings import default_setting_config, validate_setting_config
# main
from app.services.tickets import (
    assert_support_or_admin,
    assert_ticket_access,
    create_history,
    list_tickets_for_user,
    transition_status,
)

app = FastAPI(title="core-api")

logger = logging.getLogger("core-api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = correlation_id
    return response


@app.on_event("startup")
def startup() -> None:
    db = SessionLocal()
    try:
        admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin123")
        support_email = os.getenv("BOOTSTRAP_SUPPORT_EMAIL", "support@example.com")
        support_password = os.getenv("BOOTSTRAP_SUPPORT_PASSWORD", "support123")
        user_email = os.getenv("BOOTSTRAP_USER_EMAIL", "user@example.com")
        user_password = os.getenv("BOOTSTRAP_USER_PASSWORD", "user12345")

        bootstrap_data = [
            (admin_email, admin_password, UserRole.ADMIN, os.getenv("BOOTSTRAP_ADMIN_PHONE", "+79990000001")),
            (support_email, support_password, UserRole.SUPPORT, os.getenv("BOOTSTRAP_SUPPORT_PHONE", "+79990000002")),
            (user_email, user_password, UserRole.USER, os.getenv("BOOTSTRAP_USER_PHONE", "+79990000003")),
        ]
        for email, raw_password, role, phone_number in bootstrap_data:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                db.add(User(email=email, password_hash=hash_password(raw_password), role=role, phone_number=phone_number))
            elif not existing.phone_number:
                existing.phone_number = phone_number
                db.add(existing)
        db.commit()
        maybe_validate_sso_startup(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar_one()
    return {"status": "ok", "db": value}


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if os.getenv("AUTH_LOCAL_DISABLED", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Local login disabled")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(user))


@app.get("/api/v1/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@app.get("/api/v1/auth/sso/login")
async def sso_login(request: Request, db: Session = Depends(get_db)) -> dict:
    conf = load_active_sso_config(db)
    if not conf:
        raise HTTPException(status_code=404, detail="SSO configuration not found")
    provider_type, cfg = conf
    adapter = get_adapter(provider_type)
    redirect_url = await adapter.get_login_redirect(request, cfg)
    return {"provider": provider_type, "redirect_url": redirect_url}


@app.get("/api/v1/auth/sso/callback")
async def sso_callback(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    conf = load_active_sso_config(db)
    if not conf:
        raise HTTPException(status_code=404, detail="SSO configuration not found")
    provider_type, cfg = conf
    adapter = get_adapter(provider_type)
    identity = await adapter.handle_callback(request, cfg)
    token = complete_sso_login(db, provider_type, identity)
    return TokenResponse(access_token=token)


@app.get("/api/v1/admin/sso/config", response_model=SSOConfigResponse | None)
def get_sso_config(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SSOProviderConfig).order_by(SSOProviderConfig.id.desc()).first()
    if not row:
        return None
    return SSOConfigResponse(
        id=row.id,
        provider_type=row.provider_type.value,
        enabled=row.enabled,
        config=json.loads(row.config_json),
    )


@app.post("/api/v1/admin/sso/config", response_model=SSOConfigResponse)
def upsert_sso_config(
    payload: SSOConfigUpsertRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SSOConfigResponse:
    try:
        provider_type = SSOProviderType(payload.provider_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="provider_type must be OIDC or SAML") from exc

    row = db.query(SSOProviderConfig).order_by(SSOProviderConfig.id.desc()).first()
    if not row:
        row = SSOProviderConfig(provider_type=provider_type, enabled=payload.enabled, config_json=json.dumps(payload.config))
    else:
        row.provider_type = provider_type
        row.enabled = payload.enabled
        row.config_json = json.dumps(payload.config)
        row.updated_at = datetime.now(UTC)

    if payload.enabled:
        if provider_type == SSOProviderType.OIDC:
            validate_oidc_config(payload.config)
        else:
            validate_saml_config(payload.config)

    db.add(row)
    db.commit()
    db.refresh(row)
    return SSOConfigResponse(id=row.id, provider_type=row.provider_type.value, enabled=row.enabled, config=json.loads(row.config_json))


speaker_recognizer = LocalSpeakerRecognizer()


@app.post("/api/v1/speaker/enroll", response_model=SpeakerEnrollResponse)
def speaker_enroll(
    payload: SpeakerEnrollRequest,
    request: Request,
    authorization: str = Header(default=""),
    x_service_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> SpeakerEnrollResponse:
    is_service = x_service_token == os.getenv("SERVICE_TOKEN", "dev-service-token")
    if is_service:
        if payload.user_id is None:
            raise HTTPException(status_code=422, detail="user_id is required for service enrollment")
        target_user_id = payload.user_id
    else:
        user = get_current_user(authorization, db)
        target_user_id = user.id

    profile = speaker_recognizer.enroll(
        db=db,
        user_id=target_user_id,
        audio_sample=payload.audio_sample_b64,
        consent=payload.consent,
        correlation_id=request.state.correlation_id,
    )
    return SpeakerEnrollResponse(user_id=target_user_id, samples_count=profile.samples_count, consent_given=profile.consent_given)


@app.post("/api/v1/speaker/identify", response_model=SpeakerIdentifyResponse)
def speaker_identify(
    payload: SpeakerIdentifyRequest,
    request: Request,
    x_service_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> SpeakerIdentifyResponse:
    if x_service_token != os.getenv("SERVICE_TOKEN", "dev-service-token"):
        raise HTTPException(status_code=401, detail="Invalid service token")
    result = speaker_recognizer.identify(
        db=db,
        phone_number=payload.phone_number,
        audio_sample=payload.audio_sample_b64,
        correlation_id=request.state.correlation_id,
    )
    return SpeakerIdentifyResponse(
        user_id=result.user_id,
        confidence=result.confidence,
        reasons=result.reasons,
        consent_required=result.consent_required,
    )


@app.post("/api/v1/tickets")
def create_ticket(
    payload: TicketCreatePortalRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = Ticket(
        owner_user_id=user.id,
        subject=payload.subject,
        description=payload.description,
        channel=payload.channel,
        status=TicketStatus.NEW,
        updated_at=datetime.now(UTC),
    )
    db.add(ticket)
    db.flush()
    create_history(
        db,
        ticket_id=ticket.id,
        actor_user_id=user.id,
        action="ticket_created",
        from_status=None,
        to_status=ticket.status,
        correlation_id=request.state.correlation_id,
    )
    db.commit()
    db.refresh(ticket)
    return {"id": ticket.id, "status": ticket.status}


@app.get("/api/v1/tickets")
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    items = list_tickets_for_user(db, user)
    return {
        "items": [
            {
                "id": t.id,
                "owner_user_id": t.owner_user_id,
                "assigned_user_id": t.assigned_user_id,
                "subject": t.subject,
                "description": t.description,
                "status": t.status,
                "channel": t.channel,
            }
            for t in items
        ]
    }


@app.get("/api/v1/tickets/{ticket_id}")
def ticket_details(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)
    return {
        "id": ticket.id,
        "owner_user_id": ticket.owner_user_id,
        "assigned_user_id": ticket.assigned_user_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "channel": ticket.channel,
    }


@app.post("/api/v1/tickets/{ticket_id}/comments")
def add_comment(
    ticket_id: int,
    payload: TicketCommentRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)

    comment = TicketComment(ticket_id=ticket.id, author_user_id=user.id, content=payload.content)
    db.add(comment)
    create_history(
        db,
        ticket_id=ticket.id,
        actor_user_id=user.id,
        action="comment_added",
        correlation_id=request.state.correlation_id,
        metadata={"comment": payload.content[:100]},
    )
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "content": comment.content}


@app.get("/api/v1/tickets/{ticket_id}/history", response_model=list[TicketHistoryResponse])
def get_history(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TicketHistoryResponse]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)

    rows = db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.id.asc()).all()
    return [
        TicketHistoryResponse(
            id=r.id,
            ticket_id=r.ticket_id,
            actor_user_id=r.actor_user_id,
            action=r.action,
            from_status=r.from_status,
            to_status=r.to_status,
            metadata_json=r.metadata_json,
            correlation_id=r.correlation_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@app.post("/api/v1/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    assert_support_or_admin(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assigned = db.get(User, payload.assigned_user_id)
    if not assigned:
        raise HTTPException(status_code=404, detail="Assignee not found")

    from_status = ticket.status
    ticket.assigned_user_id = assigned.id
    ticket.status = TicketStatus.DELEGATED
    ticket.updated_at = datetime.now(UTC)
    create_history(
        db,
        ticket_id=ticket.id,
        actor_user_id=user.id,
        action="ticket_assigned",
        from_status=from_status,
        to_status=ticket.status,
        correlation_id=request.state.correlation_id,
        metadata={"assigned_user_id": assigned.id},
    )
    db.commit()
    return {"id": ticket.id, "status": ticket.status, "assigned_user_id": ticket.assigned_user_id}


@app.post("/api/v1/tickets/{ticket_id}/status")
def change_status(
    ticket_id: int,
    payload: TicketStatusRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)
    updated = transition_status(db, ticket, user, payload.status, request.state.correlation_id)
    db.commit()
    return {"id": updated.id, "status": updated.status}


@app.post("/api/v1/tickets/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    payload: TicketCloseRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)

    before_status = ticket.status
    updated = transition_status(db, ticket, user, TicketStatus.CLOSED, request.state.correlation_id)
    create_history(
        db,
        ticket_id=ticket.id,
        actor_user_id=user.id,
        action="ticket_closed",
        from_status=before_status,
        to_status=updated.status,
        correlation_id=request.state.correlation_id,
        metadata={"resolution_comment": payload.resolution_comment},
    )
    db.commit()
    return {"id": updated.id, "status": updated.status}


@app.post("/api/v1/tickets/{ticket_id}/ratings")
def rate_ticket(
    ticket_id: int,
    payload: TicketRatingRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only ticket owner can rate")
    if ticket.status != TicketStatus.CLOSED:
        raise HTTPException(status_code=422, detail="Rating available only after CLOSED")
    existing = db.query(TicketRating).filter(TicketRating.ticket_id == ticket_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rating already exists")

    rating = TicketRating(ticket_id=ticket_id, user_id=user.id, score=payload.score, comment=payload.comment)
    db.add(rating)
    create_history(
        db,
        ticket_id=ticket.id,
        actor_user_id=user.id,
        action="rating_added",
        correlation_id=request.state.correlation_id,
        metadata={"score": payload.score},
    )
    db.commit()
    return {"ticket_id": ticket_id, "score": payload.score}


@app.post("/api/v1/call-logs")
def log_call_event(
    payload: dict,
    request: Request,
    x_service_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    if x_service_token != os.getenv("SERVICE_TOKEN", "dev-service-token"):
        raise HTTPException(status_code=401, detail="Invalid service token")
    call_id = str(payload.get("call_id", ""))
    event_type = str(payload.get("event_type", ""))
    if not call_id or not event_type:
        raise HTTPException(status_code=422, detail="call_id and event_type are required")

    row = CallLog(
        call_id=call_id,
        ticket_id=payload.get("ticket_id"),
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        correlation_id=request.state.correlation_id,
    )
    db.add(row)
    db.commit()
    logger.info(
        json.dumps(
            {
                "event": "call_log_created",
                "correlation_id": request.state.correlation_id,
                "call_id": call_id,
                "ticket_id": payload.get("ticket_id"),
            },
            ensure_ascii=False,
        )
    )
    return {"id": row.id}


@app.get("/api/v1/tickets/{ticket_id}/comments")
def list_comments(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    assert_ticket_access(user, ticket)
    rows = db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id).order_by(TicketComment.id.asc()).all()
    return {
        "items": [
            {
                "id": c.id,
                "author_user_id": c.author_user_id,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
            }
            for c in rows
        ]
    }


@app.get("/api/v1/support/tickets")
def support_queue(
    status_filter: str | None = None,
    assigned_user_id: int | None = None,
    channel: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    assert_support_or_admin(user)
    q = db.query(Ticket)
    if status_filter:
        q = q.filter(Ticket.status == TicketStatus(status_filter))
    if assigned_user_id is not None:
        q = q.filter(Ticket.assigned_user_id == assigned_user_id)
    if channel:
        q = q.filter(Ticket.channel == channel)
    rows = q.order_by(Ticket.id.desc()).all()
    return {
        "items": [
            {
                "id": t.id,
                "subject": t.subject,
                "status": t.status,
                "assigned_user_id": t.assigned_user_id,
                "channel": t.channel,
            }
            for t in rows
        ]
    }


@app.post("/api/v1/tickets/{ticket_id}/assign-self")
def assign_self(ticket_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    assert_support_or_admin(user)
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    from_status = ticket.status
    ticket.assigned_user_id = user.id
    ticket.status = TicketStatus.DELEGATED
    ticket.updated_at = datetime.now(UTC)
    create_history(
        db,
        ticket.id,
        user.id,
        "ticket_assign_self",
        request.state.correlation_id,
        from_status=from_status,
        to_status=ticket.status,
    )
    db.commit()
    return {"id": ticket.id, "assigned_user_id": ticket.assigned_user_id, "status": ticket.status}


@app.get("/api/v1/admin/settings/{section}", response_model=SystemSettingResponse)
def admin_get_setting(section: str, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> SystemSettingResponse:
    row = db.query(SystemSetting).filter(SystemSetting.section == section).first()
    if not row:
# codex/define-architecture-for-support-system-e3u2rv
        config = default_setting_config(section)
        row = SystemSetting(section=section, config_json=json.dumps(config))

        row = SystemSetting(section=section, config_json=json.dumps({}))
# main
        db.add(row)
        db.commit()
        db.refresh(row)
    return SystemSettingResponse(section=row.section, config=json.loads(row.config_json))


@app.post("/api/v1/admin/settings/{section}", response_model=SystemSettingResponse)
def admin_set_setting(
    section: str,
    payload: SystemSettingRequest,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemSettingResponse:
# codex/define-architecture-for-support-system-e3u2rv
    validated_config = validate_setting_config(section, payload.config)
    row = db.query(SystemSetting).filter(SystemSetting.section == section).first()
    if not row:
        row = SystemSetting(section=section, config_json=json.dumps(validated_config), updated_by_user_id=user.id)
    else:
        row.config_json = json.dumps(validated_config)

    row = db.query(SystemSetting).filter(SystemSetting.section == section).first()
    if not row:
        row = SystemSetting(section=section, config_json=json.dumps(payload.config), updated_by_user_id=user.id)
    else:
        row.config_json = json.dumps(payload.config)
# main
        row.updated_by_user_id = user.id
        row.updated_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SystemSettingResponse(section=row.section, config=json.loads(row.config_json))


# codex/define-architecture-for-support-system-e3u2rv



# main
@app.get("/api/v1/service/settings/{section}")
def service_get_setting(section: str, x_service_token: str = Header(default=""), db: Session = Depends(get_db)) -> SystemSettingResponse:
    if x_service_token != os.getenv("SERVICE_TOKEN", "dev-service-token"):
        raise HTTPException(status_code=401, detail="Invalid service token")
    row = db.query(SystemSetting).filter(SystemSetting.section == section).first()
    if not row:
# codex/define-architecture-for-support-system-e3u2rv
        return SystemSettingResponse(section=section, config=default_setting_config(section))

        return SystemSettingResponse(section=section, config={})
# main
    return SystemSettingResponse(section=row.section, config=json.loads(row.config_json))


@app.get("/api/v1/public/branding")
def public_branding(db: Session = Depends(get_db)) -> dict:
    row = db.query(SystemSetting).filter(SystemSetting.section == "branding").first()
    return {"config": json.loads(row.config_json) if row else {}}

# codex/define-architecture-for-support-system-e3u2rv


# main
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )
