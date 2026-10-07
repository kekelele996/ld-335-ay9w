from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.messages import ErrorMessages
from app.models.settlement import SettlementRecord
from app.schemas.settlement import ExpenseUploadRequest, ExpenseUploadResponse, PreSettlementRequest, PreSettlementResponse, SettlementConfirmRequest, SettlementResponse


def upload_expenses(payload: ExpenseUploadRequest, principal: dict) -> ExpenseUploadResponse:
    item_codes = [item.item_code for item in payload.items]
    if len(item_codes) != len(set(item_codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.DUPLICATED_ITEM)
    total = sum((item.amount for item in payload.items), Decimal("0.00"))
    return ExpenseUploadResponse(batch_no=f"UP{uuid4().hex[:12].upper()}", accepted_count=len(payload.items), total_amount=total)


def pre_settle(payload: PreSettlementRequest, principal: dict) -> PreSettlementResponse:
    total = sum((item.amount for item in payload.items), Decimal("0.00"))
    deductible = Decimal("650.00") if payload.region.endswith("市") else Decimal("450.00")
    reimbursable = max(total - deductible, Decimal("0.00"))
    ratio = Decimal("0.78")
    reimbursed = (reimbursable * ratio).quantize(Decimal("0.01"))
    account_pay = min(Decimal("800.00"), max(total - reimbursed, Decimal("0.00"))).quantize(Decimal("0.01"))
    self_pay = (total - reimbursed - account_pay).quantize(Decimal("0.01"))
    return PreSettlementResponse(
        total_amount=total,
        reimbursed_amount=reimbursed,
        account_pay_amount=account_pay,
        self_pay_amount=self_pay,
        deductible=deductible,
        reimbursement_ratio=ratio,
        details=payload.items,
    )


def confirm_settlement(payload: SettlementConfirmRequest, db: Session, principal: dict) -> SettlementResponse:
    record = SettlementRecord(
        settlement_no=f"JS{uuid4().hex[:14].upper()}",
        batch_no=payload.batch_no,
        insured_id=payload.insured_id,
        total_amount=payload.pre_settlement.total_amount,
        reimbursed_amount=payload.pre_settlement.reimbursed_amount,
        self_pay_amount=payload.pre_settlement.self_pay_amount,
        status="SUCCESS",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return SettlementResponse.model_validate(record)


def reverse_settlement(settlement_no: str, db: Session, principal: dict) -> SettlementResponse:
    record = db.scalar(select(SettlementRecord).where(SettlementRecord.settlement_no == settlement_no))
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorMessages.SETTLEMENT_NOT_FOUND)
    if record.status == "REVERSED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ErrorMessages.SETTLEMENT_REVERSED)
    record.status = "REVERSED"
    db.commit()
    db.refresh(record)
    return SettlementResponse.model_validate(record)


def query_settlements(db: Session, principal: dict, settlement_no: str | None, insured_id: str | None, start: date | None, end: date | None) -> list[SettlementResponse]:
    statement = select(SettlementRecord)
    if settlement_no:
        statement = statement.where(SettlementRecord.settlement_no == settlement_no)
    if insured_id:
        statement = statement.where(SettlementRecord.insured_id == insured_id)
    if start:
        statement = statement.where(SettlementRecord.created_at >= datetime.combine(start, time.min))
    if end:
        statement = statement.where(SettlementRecord.created_at < datetime.combine(end + timedelta(days=1), time.min))
    records = db.scalars(statement.order_by(SettlementRecord.created_at.desc())).all()
    return [SettlementResponse.model_validate(record) for record in records]
