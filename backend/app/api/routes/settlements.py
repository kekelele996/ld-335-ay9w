from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_principal
from app.db.session import get_db
from app.schemas.settlement import (
    ExpenseUploadRequest,
    ExpenseUploadResponse,
    PreSettlementRequest,
    PreSettlementResponse,
    SettlementConfirmRequest,
    SettlementResponse,
)
from app.services.settlement_service import confirm_settlement, query_settlements, reverse_settlement, upload_expenses, pre_settle

router = APIRouter()


@router.post("/expenses", response_model=ExpenseUploadResponse)
def upload(payload: ExpenseUploadRequest, principal: dict = Depends(require_principal)) -> ExpenseUploadResponse:
    return upload_expenses(payload, principal)


@router.post("/pre-settle", response_model=PreSettlementResponse)
def calculate(payload: PreSettlementRequest, principal: dict = Depends(require_principal)) -> PreSettlementResponse:
    return pre_settle(payload, principal)


@router.post("/confirm", response_model=SettlementResponse)
def confirm(payload: SettlementConfirmRequest, db: Session = Depends(get_db), principal: dict = Depends(require_principal)) -> SettlementResponse:
    return confirm_settlement(payload, db, principal)


@router.post("/{settlement_no}/reverse", response_model=SettlementResponse)
def reverse(settlement_no: str, db: Session = Depends(get_db), principal: dict = Depends(require_principal)) -> SettlementResponse:
    return reverse_settlement(settlement_no, db, principal)


@router.get("", response_model=list[SettlementResponse])
def query(
    settlement_no: str | None = None,
    insured_id: str | None = None,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_principal),
) -> list[SettlementResponse]:
    return query_settlements(db, principal, settlement_no, insured_id, start, end)
