from fastapi import APIRouter

from app.api.routes import auth, insured, reconciliation, settlements

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(insured.router, prefix="/insured", tags=["insured"])
api_router.include_router(settlements.router, prefix="/settlements", tags=["settlements"])
api_router.include_router(reconciliation.router, prefix="/reconciliation", tags=["reconciliation"])
