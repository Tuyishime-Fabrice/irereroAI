import pyotp
from fastapi.testclient import TestClient

from irerero_api.demo import DEMO_PASSWORD, DEMO_TOTP_SECRET


def test_staff_login_and_me(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "planner.gicumbi@demo.irereroai.rw", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "district_planner"
    assert me["scope_name"] == "Gicumbi"


def test_wrong_password_is_refused(client: TestClient) -> None:
    wrong = "not-the-password"  # pragma: allowlist secret
    response = client.post(
        "/auth/login", json={"email": "planner.gicumbi@demo.irereroai.rw", "password": wrong}
    )
    assert response.status_code == 401


def test_admin_needs_a_totp_code(client: TestClient) -> None:
    body = {"email": "admin@demo.irereroai.rw", "password": DEMO_PASSWORD}
    assert client.post("/auth/login", json=body).status_code == 401
    code = pyotp.TOTP(DEMO_TOTP_SECRET).now()
    assert client.post("/auth/login", json=body | {"totp_code": code}).status_code == 200


def test_parent_signs_in_with_a_one_time_code(client: TestClient) -> None:
    requested = client.post("/auth/otp/request", json={"phone": "0700 000 099"}).json()
    assert requested["demo_code"]
    wrong = client.post("/auth/otp/verify", json={"phone": "+250700000099", "code": "000000"})
    assert wrong.status_code == 401
    ok = client.post(
        "/auth/otp/verify", json={"phone": "+250700000099", "code": requested["demo_code"]}
    )
    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "parent"


def test_caregiver_signs_in_with_phone_and_centre_code(client: TestClient) -> None:
    ok = client.post("/auth/caregiver", json={"phone": "0700000002", "centre_code": "ECD-GIC-001"})
    assert ok.status_code == 200
    wrong = client.post(
        "/auth/caregiver", json={"phone": "0700000002", "centre_code": "ECD-GIC-002"}
    )
    assert wrong.status_code == 401


def test_refresh_token_rotates(client: TestClient) -> None:
    tokens = client.post("/demo/login/national_analyst").json()
    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_endpoints_need_a_session(client: TestClient) -> None:
    assert client.get("/alerts").status_code == 401
    assert client.get("/centres").status_code == 401
