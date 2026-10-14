from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from irerero_api.auth.principal import Principal
from irerero_api.auth.tokens import InvalidTokenError, principal_from_access
from irerero_api.config import get_settings
from irerero_contract.enums import Role

bearer = HTTPBearer(auto_error=False)


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> Principal:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    try:
        return principal_from_access(credentials.credentials, get_settings())
    except InvalidTokenError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired") from error


def require_planner(principal: Principal = Depends(current_principal)) -> Principal:  # noqa: B008
    if principal.role is not Role.DISTRICT_PLANNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot use this")
    return principal


Planner = Annotated[Principal, Depends(require_planner)]
