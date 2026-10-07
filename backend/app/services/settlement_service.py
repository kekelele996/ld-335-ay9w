from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.messages import ErrorMessages
from app.models.settlement import SettlementRecord
from app.schemas.settlement import (
    ExpenseItem,
    ExpenseUploadRequest,
    ExpenseUploadResponse,
    PreSettlementRequest,
    PreSettlementResponse,
    SettlementConfirmRequest,
    SettlementDetail,
    SettlementResponse,
)

# 统一报销（统筹支付）比例，只作用于扣除起付线后的报销基数
REIMBURSEMENT_RATIO = Decimal("0.78")
# 预结算请求未带账户余额时的兜底余额
DEFAULT_ACCOUNT_BALANCE = Decimal("800.00")
# 乙类费用自付口径：以明细上填写的自付比例为准（明细自付比例优先于目录固定比例）
CLASS_B_BASIS = "ITEM_SELF_PAY_RATIO"
CLASS_B_BASIS_DESC = (
    "乙类费用以该条明细填写的自付比例为准（明细自付比例优先于目录固定比例）："
    "先按明细自付比例扣除先行自付部分，剩余金额计入报销基数；"
    "甲类整条计入报销基数，丙类整条自费、不计入报销基数。"
    "若乙类改按目录固定比例（视同甲类整条进基数），报销金额会更高、自费更低，"
    "两种口径下同一张单结果不同，本网关统一采用明细自付比例口径。"
)
CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS)


@dataclass
class SettlementBreakdown:
    total_amount: Decimal
    class_a_amount: Decimal
    class_b_amount: Decimal
    class_b_self_pay_amount: Decimal
    class_c_self_pay_amount: Decimal
    reimbursement_base: Decimal
    reimbursed_amount: Decimal
    account_pay_amount: Decimal
    self_pay_amount: Decimal
    deductible: Decimal
    below_deductible: bool
    account_balance: Decimal
    details: list[SettlementDetail]


def _deductible_for(region: str) -> Decimal:
    return Decimal("650.00") if region.endswith("市") else Decimal("450.00")


def calculate_settlement(
    region: str,
    items: list[ExpenseItem],
    account_balance: Decimal | None = None,
) -> SettlementBreakdown:
    """按目录类别分开计算的统一口径，预结算、正式结算、查询、对账共用。

    - 甲类：整条明细计入报销基数，无目录自付。
    - 乙类：以明细自付比例为准，先扣先行自付，剩余计入报销基数。
    - 丙类：整条自费，不进报销基数。
    - 报销基数不足起付线时统筹报销记 0。
    - 个人账户支付同时不超过账户余额和个人负担总额。
    """
    balance = _money(account_balance if account_balance is not None else DEFAULT_ACCOUNT_BALANCE)
    deductible = _deductible_for(region)

    details: list[SettlementDetail] = []
    total = Decimal("0.00")
    class_a = Decimal("0.00")
    class_b = Decimal("0.00")
    class_b_self = Decimal("0.00")
    class_c_self = Decimal("0.00")
    base = Decimal("0.00")

    for item in items:
        amount = _money(item.amount)
        total += amount
        if item.catalog_class == "甲类":
            catalog_self = Decimal("0.00")
            eligible = amount
            class_a += amount
        elif item.catalog_class == "乙类":
            catalog_self = _money(amount * item.self_pay_ratio)
            eligible = amount - catalog_self
            class_b += amount
            class_b_self += catalog_self
        else:  # 丙类：整条自费，不进基数
            catalog_self = amount
            eligible = Decimal("0.00")
            class_c_self += amount
        base += eligible
        details.append(
            SettlementDetail(
                item_code=item.item_code,
                name=item.name,
                category=item.category,
                catalog_class=item.catalog_class,
                unit_price=item.unit_price,
                quantity=item.quantity,
                amount=amount,
                self_pay_ratio=item.self_pay_ratio,
                catalog_self_pay_amount=_money(catalog_self),
                eligible_amount=_money(eligible),
            )
        )

    base = _money(base)
    # 不足起付线时报销记零，起付线计入个人负担
    below_deductible = base < deductible
    reimbursable = max(base - deductible, Decimal("0.00")) if not below_deductible else Decimal("0.00")
    reimbursed = _money(reimbursable * REIMBURSEMENT_RATIO)
    personal_burden = _money(total - reimbursed)
    # 个人账户支付：不超过账户余额，也不超过个人负担总额
    account_pay = _money(min(balance, max(personal_burden, Decimal("0.00"))))
    self_pay = _money(personal_burden - account_pay)

    return SettlementBreakdown(
        total_amount=_money(total),
        class_a_amount=_money(class_a),
        class_b_amount=_money(class_b),
        class_b_self_pay_amount=_money(class_b_self),
        class_c_self_pay_amount=_money(class_c_self),
        reimbursement_base=base,
        reimbursed_amount=reimbursed,
        account_pay_amount=account_pay,
        self_pay_amount=self_pay,
        deductible=deductible,
        below_deductible=below_deductible,
        account_balance=balance,
        details=details,
    )


def upload_expenses(payload: ExpenseUploadRequest, principal: dict) -> ExpenseUploadResponse:
    item_codes = [item.item_code for item in payload.items]
    if len(item_codes) != len(set(item_codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.DUPLICATED_ITEM)
    total = sum((item.amount for item in payload.items), Decimal("0.00"))
    return ExpenseUploadResponse(batch_no=f"UP{uuid4().hex[:12].upper()}", accepted_count=len(payload.items), total_amount=total)


def pre_settle(payload: PreSettlementRequest, principal: dict) -> PreSettlementResponse:
    breakdown = calculate_settlement(payload.region, payload.items, payload.account_balance)
    return PreSettlementResponse(
        region=payload.region,
        total_amount=breakdown.total_amount,
        class_a_amount=breakdown.class_a_amount,
        class_b_amount=breakdown.class_b_amount,
        class_b_self_pay_amount=breakdown.class_b_self_pay_amount,
        class_c_self_pay_amount=breakdown.class_c_self_pay_amount,
        reimbursement_base=breakdown.reimbursement_base,
        reimbursed_amount=breakdown.reimbursed_amount,
        account_pay_amount=breakdown.account_pay_amount,
        self_pay_amount=breakdown.self_pay_amount,
        deductible=breakdown.deductible,
        below_deductible=breakdown.below_deductible,
        reimbursement_ratio=REIMBURSEMENT_RATIO,
        account_balance=breakdown.account_balance,
        class_b_basis=CLASS_B_BASIS,
        class_b_basis_desc=CLASS_B_BASIS_DESC,
        details=breakdown.details,
    )


def confirm_settlement(payload: SettlementConfirmRequest, db: Session, principal: dict) -> SettlementResponse:
    pre = payload.pre_settlement
    # 正式结算以服务端统一口径重算为准，不信任调用方回传的金额，保证与医保局对账一致
    breakdown = calculate_settlement(pre.region, pre.details, pre.account_balance)
    record = SettlementRecord(
        settlement_no=f"JS{uuid4().hex[:14].upper()}",
        batch_no=payload.batch_no,
        insured_id=payload.insured_id,
        total_amount=breakdown.total_amount,
        reimbursed_amount=breakdown.reimbursed_amount,
        account_pay_amount=breakdown.account_pay_amount,
        self_pay_amount=breakdown.self_pay_amount,
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
