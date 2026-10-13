from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from irerero_api.main import app

Login = Callable[[str], dict[str, str]]


@pytest.fixture(scope="session")
def client(demo_engine: Engine) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth(client: TestClient) -> Login:
    """Authorization headers for the demo account of a role."""
    cache: dict[str, dict[str, str]] = {}

    def login(role: str) -> dict[str, str]:
        if role not in cache:
            token = client.post(f"/demo/login/{role}").json()["access_token"]
            cache[role] = {"Authorization": f"Bearer {token}"}
        return cache[role]

    return login
