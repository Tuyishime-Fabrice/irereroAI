"""The demo planner. Credentials are shown on the sign-in screen in demo mode only."""

from sqlalchemy import Connection, insert

from irerero_api.demo import DEMO_PASSWORD
from irerero_contract.enums import Role
from irerero_contract.passwords import hash_secret
from irerero_contract.tables import UserAccount
from pipelines.demo.config import DEMO_DISTRICT, stable_id

DEMO_PLANNER_EMAIL = "planner.gicumbi@demo.irereroai.rw"


def load_accounts(conn: Connection) -> int:
    conn.execute(
        insert(UserAccount).values(
            id=stable_id("account", "district_planner"),
            role=Role.DISTRICT_PLANNER,
            district_code=DEMO_DISTRICT,
            display_name="Demo planner, Gicumbi",
            email=DEMO_PLANNER_EMAIL,
            password_hash=hash_secret(DEMO_PASSWORD),
        )
    )
    return 1
