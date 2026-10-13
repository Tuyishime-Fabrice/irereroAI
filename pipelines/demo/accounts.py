"""One demo account per role. Credentials are shown on the login screen in demo mode only."""

from dataclasses import dataclass

from sqlalchemy import Connection, insert

from irerero_contract.enums import Role, ScopeLevel
from irerero_contract.passwords import hash_secret
from irerero_contract.tables import UserAccount
from pipelines.demo.config import DEMO_DISTRICT, OFFICER_SECTOR, stable_id
from pipelines.demo.story import STORY_BY_ROLE

# Demo-only credentials, published in the README. Never reuse them anywhere real.
DEMO_PASSWORD = "irerero-demo-2026"  # noqa: S105  # pragma: allowlist secret
DEMO_TOTP_SECRET = "JBSWY3DPEHPK3PXPIRERERO2"  # noqa: S105  # pragma: allowlist secret


@dataclass(frozen=True)
class DemoAccount:
    key: str
    role: Role
    scope_level: ScopeLevel
    scope_code: str | None
    display_name: str
    email: str | None = None
    phone: str | None = None


CAREGIVER_CENTRE = STORY_BY_ROLE["caregiver_home"].code

DEMO_ACCOUNTS = (
    DemoAccount("parent", Role.PARENT, ScopeLevel.NONE, None, "Demo parent", phone="+250700000001"),
    DemoAccount(
        "caregiver",
        Role.CAREGIVER,
        ScopeLevel.CENTRE,
        CAREGIVER_CENTRE,
        "Demo caregiver, Irerero Ineza",
        phone="+250700000002",
    ),
    DemoAccount(
        "sector_officer",
        Role.SECTOR_OFFICER,
        ScopeLevel.SECTOR,
        OFFICER_SECTOR,
        "Demo ECD officer, Byumba",
        email="officer.byumba@demo.irereroai.rw",
    ),
    DemoAccount(
        "district_planner",
        Role.DISTRICT_PLANNER,
        ScopeLevel.DISTRICT,
        DEMO_DISTRICT,
        "Demo planner, Gicumbi",
        email="planner.gicumbi@demo.irereroai.rw",
    ),
    DemoAccount(
        "national_analyst",
        Role.NATIONAL_ANALYST,
        ScopeLevel.NATIONAL,
        None,
        "Demo national analyst",
        email="analyst@demo.irereroai.rw",
    ),
    DemoAccount(
        "admin",
        Role.ADMIN,
        ScopeLevel.NATIONAL,
        None,
        "Demo system admin",
        email="admin@demo.irereroai.rw",
    ),
)


def account_id(key: str) -> object:
    return stable_id("account", key)


def load_accounts(conn: Connection) -> int:
    password_hash = hash_secret(DEMO_PASSWORD)
    for account in DEMO_ACCOUNTS:
        is_staff = account.email is not None
        conn.execute(
            insert(UserAccount).values(
                id=account_id(account.key),
                role=account.role,
                scope_level=account.scope_level,
                scope_code=account.scope_code,
                display_name=account.display_name,
                email=account.email,
                phone=account.phone,
                password_hash=password_hash if is_staff else None,
                totp_secret=DEMO_TOTP_SECRET if account.role is Role.ADMIN else None,
            )
        )
    return len(DEMO_ACCOUNTS)
