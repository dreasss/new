import json
from datetime import UTC, datetime

from app.models import Ticket, TicketHistory, TicketStatus, User, UserRole
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

ALLOWED_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.IN_PROGRESS, TicketStatus.DELEGATED, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {TicketStatus.WAITING_USER, TicketStatus.DELEGATED, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.WAITING_USER: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.DELEGATED: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: set(),
}


def assert_ticket_access(user: User, ticket: Ticket) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.SUPPORT:
        return
    if ticket.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def assert_support_or_admin(user: User) -> None:
    if user.role not in {UserRole.SUPPORT, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Support/Admin only")


def create_history(
    db: Session,
    ticket_id: int,
    actor_user_id: int | None,
    action: str,
    correlation_id: str,
    from_status: TicketStatus | None = None,
    to_status: TicketStatus | None = None,
    metadata: dict | None = None,
) -> None:
    row = TicketHistory(
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        correlation_id=correlation_id,
    )
    db.add(row)


def transition_status(
    db: Session,
    ticket: Ticket,
    actor: User,
    to_status: TicketStatus,
    correlation_id: str,
) -> Ticket:
    from_status = ticket.status
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid transition: {from_status.value} -> {to_status.value}",
        )

    if actor.role == UserRole.USER and ticket.owner_user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if actor.role == UserRole.USER and to_status in {TicketStatus.DELEGATED, TicketStatus.RESOLVED}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot set this status")

    ticket.status = to_status
    ticket.updated_at = datetime.now(UTC)
    create_history(
        db=db,
        ticket_id=ticket.id,
        actor_user_id=actor.id,
        action="status_changed",
        correlation_id=correlation_id,
        from_status=from_status,
        to_status=to_status,
    )
    db.add(ticket)
    return ticket


def list_tickets_for_user(db: Session, user: User) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.id.desc())
    if user.role == UserRole.USER:
        stmt = stmt.where(Ticket.owner_user_id == user.id)
    return list(db.scalars(stmt).all())
