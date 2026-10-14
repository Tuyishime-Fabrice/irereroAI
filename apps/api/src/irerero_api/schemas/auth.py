import uuid

from pydantic import BaseModel

from irerero_contract.enums import Role


class Login(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class Me(BaseModel):
    id: uuid.UUID
    role: Role
    district_code: str
    district_name: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Me
