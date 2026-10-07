from fastapi import APIRouter, Depends

from app.api.dependencies import require_api_key
from app.core.security import create_token
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest, _: str = Depends(require_api_key)) -> TokenResponse:
    return TokenResponse(access_token=create_token(payload.client_id, payload.scopes))
