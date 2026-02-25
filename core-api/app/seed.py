"""Seed demo data in PostgreSQL for local manual testing."""

from datetime import UTC, datetime

from app.db.database import SessionLocal
from app.models import Ticket, TicketComment, TicketStatus, User, UserRole
from app.services.auth import hash_password


def get_or_create_user(db, email: str, password: str, role: UserRole, phone: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        if not user.phone_number:
            user.phone_number = phone
            db.add(user)
        return user
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        phone_number=phone,
    )
    db.add(user)
    db.flush()
    return user


def create_ticket_with_comment(db, owner_id: int, subject: str, status: TicketStatus, channel: str, comment: str) -> None:
    existing = db.query(Ticket).filter(Ticket.subject == subject).first()
    if existing:
        return
    t = Ticket(
        owner_user_id=owner_id,
        subject=subject,
        description=f"Автосоздано: {subject}",
        channel=channel,
        status=status,
        updated_at=datetime.now(UTC),
    )
    db.add(t)
    db.flush()
    db.add(TicketComment(ticket_id=t.id, author_user_id=owner_id, content=comment))


def main() -> None:
    db = SessionLocal()
    try:
        admin = get_or_create_user(db, "admin@example.com", "admin123", UserRole.ADMIN, "+79990000001")
        support = get_or_create_user(db, "support@example.com", "support123", UserRole.SUPPORT, "+79990000002")
        user = get_or_create_user(db, "user@example.com", "user12345", UserRole.USER, "+79990000003")
        get_or_create_user(db, "demo.user@example.com", "demo12345", UserRole.USER, "+79998887766")

        create_ticket_with_comment(db, user.id, "Нет сети в кабинете", TicketStatus.NEW, "voice", "Звонок от пользователя")
        create_ticket_with_comment(db, user.id, "Не работает принтер", TicketStatus.IN_PROGRESS, "web", "Принято поддержкой")
        create_ticket_with_comment(db, user.id, "Сброс пароля", TicketStatus.CLOSED, "web", "Решено и закрыто")
        create_ticket_with_comment(db, support.id, "Мониторинг SIP", TicketStatus.DELEGATED, "voice", "Передано сетевой команде")
        create_ticket_with_comment(db, admin.id, "Обновление брендинга", TicketStatus.WAITING_USER, "web", "Ожидаем подтверждение")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
