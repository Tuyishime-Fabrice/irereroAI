import uuid
from dataclasses import dataclass

from irerero_contract.enums import Role, ScopeLevel


@dataclass(frozen=True)
class Principal:
    """The signed-in account, as carried in the access token."""

    id: uuid.UUID
    role: Role
    scope_level: ScopeLevel
    scope_code: str | None
