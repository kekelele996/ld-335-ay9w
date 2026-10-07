from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.messages import ErrorMessages
from app.core.security import decode_token

bearer_scheme = HTTPBearer()


def require_api_key(x_api_key: str = Header(alias="X-API-Key")) -> str:
    if x_api_key != settings.api_key_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorMessages.INVALID_API_KEY)
    return x_api_key


def require_principal(
    _: str = Depends(require_api_key),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    return decode_token(credentials.credentials)
