import os

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_login_create_ticket_and_support_queue() -> None:
    if not os.getenv("RUN_DB_INTEGRATION"):
        pytest.skip("RUN_DB_INTEGRATION is not set")

    c = TestClient(app)
    user = c.post(
        "/api/v1/auth/login",
        json={
            "email": os.getenv("BOOTSTRAP_USER_EMAIL", "user@example.com"),
            "password": os.getenv("BOOTSTRAP_USER_PASSWORD", "user12345"),
        },
    )
    support = c.post(
        "/api/v1/auth/login",
        json={
            "email": os.getenv("BOOTSTRAP_SUPPORT_EMAIL", "support@example.com"),
            "password": os.getenv("BOOTSTRAP_SUPPORT_PASSWORD", "support123"),
        },
    )
    assert user.status_code == 200
    assert support.status_code == 200

    ut = user.json()["access_token"]
    st = support.json()["access_token"]

    created = c.post(
        "/api/v1/tickets",
        json={"subject": "Portal flow", "description": "created from integration", "channel": "web"},
        headers={"Authorization": f"Bearer {ut}"},
    )
    assert created.status_code == 200

    queue = c.get("/api/v1/support/tickets?channel=web", headers={"Authorization": f"Bearer {st}"})
    assert queue.status_code == 200
    assert any(t["id"] == created.json()["id"] for t in queue.json()["items"])
