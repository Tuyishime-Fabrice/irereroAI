import uuid

from pydantic import BaseModel, Field

from irerero_contract.enums import Role, ScopeLevel


class StaffLogin(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


class CaregiverLogin(BaseModel):
    phone: str
    centre_code: str


class OtpRequest(BaseModel):
    phone: str


class OtpRequested(BaseModel):
    expires_in_seconds: int
    demo_code: str | None = Field(
        default=None, description="Shown only in demo mode, where no SMS is sent"
    )


class OtpVerify(BaseModel):
    phone: str
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class Me(BaseModel):
    id: uuid.UUID
    role: Role
    scope_level: ScopeLevel
    scope_code: str | None
    scope_name: str | None
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Me
