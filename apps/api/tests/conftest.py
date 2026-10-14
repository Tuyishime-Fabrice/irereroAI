from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from irerero_api.main import app

Headers = dict[str, str]


@pytest.fixture(scope="session")
def client(demo_engine: Engine) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def planner(client: TestClient) -> Headers:
    """Authorization headers for the demo planner (Gicumbi)."""
    token = client.post("/demo/login").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
