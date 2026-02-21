import os

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_user_sees_only_own_tickets() -> None:
    if not os.getenv("RUN_DB_INTEGRATION"):
        pytest.skip("RUN_DB_INTEGRATION is not set")

    client = TestClient(app)

    user_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": os.getenv("BOOTSTRAP_USER_EMAIL", "user@example.com"),
            "password": os.getenv("BOOTSTRAP_USER_PASSWORD", "user12345"),
        },
    )
    support_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": os.getenv("BOOTSTRAP_SUPPORT_EMAIL", "support@example.com"),
            "password": os.getenv("BOOTSTRAP_SUPPORT_PASSWORD", "support123"),
        },
    )

    assert user_login.status_code == 200
    assert support_login.status_code == 200

    user_token = user_login.json()["access_token"]
    support_token = support_login.json()["access_token"]

    create_resp = client.post(
        "/api/v1/tickets",
        json={"subject": "User ticket", "description": "owned by user"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert create_resp.status_code == 200

    support_create = client.post(
        "/api/v1/tickets",
        json={"subject": "Support ticket", "description": "owned by support"},
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert support_create.status_code == 200

    list_resp = client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {user_token}"})
    assert list_resp.status_code == 200
    ids = [x["id"] for x in list_resp.json()["items"]]
    assert create_resp.json()["id"] in ids
    assert support_create.json()["id"] not in ids
