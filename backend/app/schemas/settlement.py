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
    # 乙类先行自付比例；不填时按目录默认比例计算
    self_pay_ratio: Decimal | None = Field(default=None, ge=0, le=1)


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


class ItemBreakdown(BaseModel):
    item_code: str
    name: str
    catalog_class: str
    amount: Decimal
    applied_self_pay_ratio: Decimal = Field(description="实际采用的自付比例")
    ratio_source: str = Field(description="比例来源：明细自付比例 / 目录默认比例 / 类别规则")
    reimbursable_amount: Decimal = Field(description="进入报销基数的金额")
    self_amount: Decimal = Field(description="先行自付或全额自费金额")


class PreSettlementResponse(BaseModel):
    insured_id: str
    region: str
    total_amount: Decimal
    reimbursable_base: Decimal = Field(description="报销基数（起付线前）")
    reimbursed_amount: Decimal
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    account_balance: Decimal = Field(description="参与计算的个人账户余额")
    deductible: Decimal
    reimbursement_ratio: Decimal
    ratio_rule: str = Field(description="自付比例取值口径说明")
    details: list[ExpenseItem]
    item_breakdowns: list[ItemBreakdown]


class SettlementConfirmRequest(BaseModel):
    batch_no: str
    insured_id: str
    pre_settlement: PreSettlementResponse


class SettlementResponse(BaseModel):
    settlement_no: str
    batch_no: str
    insured_id: str
    total_amount: Decimal
    reimbursable_base: Decimal
    reimbursed_amount: Decimal
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    deductible: Decimal
    reimbursement_ratio: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
