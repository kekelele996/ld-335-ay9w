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
    # 身份核验返回的个人账户余额；不传时按兜底余额计算
    account_balance: Decimal | None = None
    items: list[ExpenseItem]


class SettlementDetail(BaseModel):
    item_code: str
    name: str
    category: str
    catalog_class: str
    unit_price: Decimal
    quantity: Decimal
    amount: Decimal
    self_pay_ratio: Decimal
    # 进报销基数前的目录自付：乙类先行自付、丙类整条自费、甲类为 0
    catalog_self_pay_amount: Decimal
    # 计入报销基数的金额：甲类整条、乙类扣自付后、丙类为 0
    eligible_amount: Decimal


class PreSettlementResponse(BaseModel):
    region: str
    total_amount: Decimal
    # 甲/乙/丙分类费用
    class_a_amount: Decimal
    class_b_amount: Decimal
    class_b_self_pay_amount: Decimal
    class_c_self_pay_amount: Decimal
    # 报销基数（统筹计算口径）
    reimbursement_base: Decimal
    reimbursed_amount: Decimal
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    deductible: Decimal
    below_deductible: bool
    reimbursement_ratio: Decimal
    account_balance: Decimal
    # 乙类费用采用的自付口径及说明
    class_b_basis: str
    class_b_basis_desc: str
    details: list[SettlementDetail]


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
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
