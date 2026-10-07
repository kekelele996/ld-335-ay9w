from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_principal
from app.db.session import get_db
from app.services.reconciliation_service import daily_summary

router = APIRouter()


@router.get("/daily")
def reconcile(day: date, db: Session = Depends(get_db), principal: dict = Depends(require_principal)) -> dict:
    return daily_summary(day, db, principal)
