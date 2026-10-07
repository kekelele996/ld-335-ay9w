from fastapi import APIRouter, Depends

from app.api.dependencies import require_principal
from app.schemas.insured import InsuredVerifyRequest, InsuredVerifyResponse
from app.services.insured_service import verify_insured

router = APIRouter()


@router.post("/verify", response_model=InsuredVerifyResponse)
def verify(payload: InsuredVerifyRequest, principal: dict = Depends(require_principal)) -> InsuredVerifyResponse:
    return verify_insured(payload, principal)
