import uuid
from dataclasses import dataclass

from irerero_contract.enums import Role


@dataclass(frozen=True)
class Principal:
    """The signed-in planner, as carried in the access token."""

    id: uuid.UUID
    role: Role
    district_code: str
