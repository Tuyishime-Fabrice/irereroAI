from fastapi.testclient import TestClient

from irerero_api.demo import DEMO_PASSWORD

EMAIL = "planner.gicumbi@demo.irereroai.rw"


def test_planner_login_and_me(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": EMAIL, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "district_planner"
    assert me["district_code"] == "D-GICUMBI"
    assert me["district_name"] == "Gicumbi"


def test_wrong_password_is_refused(client: TestClient) -> None:
    wrong = "not-the-password"  # pragma: allowlist secret
    response = client.post("/auth/login", json={"email": EMAIL, "password": wrong})
    assert response.status_code == 401


def test_refresh_token_rotates(client: TestClient) -> None:
    tokens = client.post("/demo/login").json()
    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_demo_account_is_published_in_demo_mode(client: TestClient) -> None:
    account = client.get("/demo/account").json()
    assert account["email"] == EMAIL and account["password"] == DEMO_PASSWORD
