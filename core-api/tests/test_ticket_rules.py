import pytest
from app.models import Ticket, TicketStatus, User, UserRole
from app.services.tickets import assert_ticket_access, transition_status
from fastapi import HTTPException


@pytest.fixture
def owner_user() -> User:
    return User(id=1, email="user@example.com", password_hash="x", role=UserRole.USER, is_active=True)


@pytest.fixture
def foreign_user() -> User:
    return User(id=2, email="u2@example.com", password_hash="x", role=UserRole.USER, is_active=True)


def test_rbac_user_cannot_access_foreign_ticket(foreign_user: User) -> None:
    ticket = Ticket(id=10, owner_user_id=1, subject="s", description="d", status=TicketStatus.NEW)
    with pytest.raises(HTTPException) as exc:
        assert_ticket_access(foreign_user, ticket)
    assert exc.value.status_code == 403


def test_invalid_status_transition_rejected(owner_user: User) -> None:
    ticket = Ticket(id=10, owner_user_id=1, subject="s", description="d", status=TicketStatus.NEW)

    class DummyDB:
        def add(self, _obj):
            pass

    db = DummyDB()
    with pytest.raises(HTTPException) as exc:
        transition_status(db, ticket, owner_user, TicketStatus.RESOLVED, "req-1")
    assert exc.value.status_code == 422


def test_valid_status_transition_logs_history(owner_user: User) -> None:
    ticket = Ticket(id=10, owner_user_id=1, subject="s", description="d", status=TicketStatus.NEW)

    class DummyDB:
        def __init__(self):
            self.add_count = 0

        def add(self, _obj):
            self.add_count += 1

    db = DummyDB()
    updated = transition_status(db, ticket, owner_user, TicketStatus.IN_PROGRESS, "req-2")
    assert updated.status == TicketStatus.IN_PROGRESS
    assert db.add_count >= 1
