from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ExpenseItem(BaseModel):
    item_code: str
    name: str
    category: str
    catalog_class: str = Field(pattern="^[甲乙丙]类$")
    unit_price: Decimal
    quantity: Decimal
    amount: Decimal
    self_pay_ratio: Decimal = Field(ge=0, le=1)


class ExpenseUploadRequest(BaseModel):
    insured_id: str
    visit_no: str
    items: list[ExpenseItem]


class ExpenseUploadResponse(BaseModel):
    batch_no: str
    accepted_count: int
    total_amount: Decimal


class PreSettlementRequest(BaseModel):
    insured_id: str
    region: str
    items: list[ExpenseItem]


class PreSettlementResponse(BaseModel):
    total_amount: Decimal
    reimbursed_amount: Decimal
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    deductible: Decimal
    reimbursement_ratio: Decimal
    details: list[ExpenseItem]


class SettlementConfirmRequest(BaseModel):
    batch_no: str
    insured_id: str
    pre_settlement: PreSettlementResponse


class SettlementResponse(BaseModel):
    settlement_no: str
    batch_no: str
    insured_id: str
    total_amount: Decimal
    reimbursed_amount: Decimal
    self_pay_amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
