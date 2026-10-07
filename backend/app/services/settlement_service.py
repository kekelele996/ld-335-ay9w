from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.messages import ErrorMessages
from app.models.settlement import SettlementRecord
from app.schemas.settlement import ExpenseItem, ExpenseUploadRequest, ExpenseUploadResponse, ItemBreakdown, PreSettlementRequest, PreSettlementResponse, SettlementConfirmRequest, SettlementResponse
from app.services.insured_service import get_account_balance

MONEY = Decimal("0.01")

# 报销比例与起付线政策（按参保地）
REIMBURSEMENT_RATIO = Decimal("0.78")
DEDUCTIBLE_CITY = Decimal("650.00")
DEDUCTIBLE_OTHER = Decimal("450.00")

# 目录默认先行自付比例：明细未填自付比例时按目录口径兜底
CATALOG_DEFAULT_SELF_PAY_RATIO = {
    "甲类": Decimal("0"),
    "乙类": Decimal("0.10"),
    "丙类": Decimal("1"),
}

RATIO_RULE = (
    "甲类全额纳入报销基数；乙类先按自付比例扣除后再进基数，自付比例以费用明细填写为准，"
    "未填写时按目录默认比例（乙类10%）计算；丙类全额自费不进基数"
)


class SettlementCalculation:
    def __init__(
        self,
        total_amount: Decimal,
        reimbursable_base: Decimal,
        reimbursed_amount: Decimal,
        account_pay_amount: Decimal,
        self_pay_amount: Decimal,
        account_balance: Decimal,
        deductible: Decimal,
        reimbursement_ratio: Decimal,
        item_breakdowns: list[ItemBreakdown],
    ) -> None:
        self.total_amount = total_amount
        self.reimbursable_base = reimbursable_base
        self.reimbursed_amount = reimbursed_amount
        self.account_pay_amount = account_pay_amount
        self.self_pay_amount = self_pay_amount
        self.account_balance = account_balance
        self.deductible = deductible
        self.reimbursement_ratio = reimbursement_ratio
        self.item_breakdowns = item_breakdowns


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _deductible_for(region: str) -> Decimal:
    return DEDUCTIBLE_CITY if region.endswith("市") else DEDUCTIBLE_OTHER


def _item_self_pay(item: ExpenseItem) -> tuple[Decimal, str]:
    """返回该明细实际采用的自付比例及来源。甲类、丙类按类别规则，不采用明细比例。"""
    if item.catalog_class == "甲类":
        return Decimal("0"), "类别规则（甲类全额纳入基数）"
    if item.catalog_class == "丙类":
        return Decimal("1"), "类别规则（丙类全额自费）"
    if item.self_pay_ratio is not None:
        return item.self_pay_ratio, "明细自付比例"
    return CATALOG_DEFAULT_SELF_PAY_RATIO["乙类"], "目录默认比例"


def calculate_settlement(items: list[ExpenseItem], region: str, account_balance: Decimal) -> SettlementCalculation:
    """预结算/正式结算统一口径：按目录类别分别进基数，起付线以下报销记零，账户支付不超余额与自费总额。"""
    deductible = _deductible_for(region)
    total = Decimal("0.00")
    base = Decimal("0.00")
    breakdowns: list[ItemBreakdown] = []
    for item in items:
        total += item.amount
        applied_ratio, ratio_source = _item_self_pay(item)
        self_amount = _money(item.amount * applied_ratio)
        reimbursable = item.amount - self_amount
        base += reimbursable
        breakdowns.append(
            ItemBreakdown(
                item_code=item.item_code,
                name=item.name,
                catalog_class=item.catalog_class,
                amount=item.amount,
                applied_self_pay_ratio=applied_ratio,
                ratio_source=ratio_source,
                reimbursable_amount=reimbursable,
                self_amount=self_amount,
            )
        )
    # 报销基数不够起付线时，报销记零
    if base <= deductible:
        reimbursed = Decimal("0.00")
    else:
        reimbursed = _money((base - deductible) * REIMBURSEMENT_RATIO)
    # 个人账户支付不超过账户余额，也不超过需个人承担的总额
    liability = total - reimbursed
    account_pay = _money(min(account_balance, liability))
    self_pay = _money(liability - account_pay)
    return SettlementCalculation(
        total_amount=total,
        reimbursable_base=base,
        reimbursed_amount=reimbursed,
        account_pay_amount=account_pay,
        self_pay_amount=self_pay,
        account_balance=account_balance,
        deductible=deductible,
        reimbursement_ratio=REIMBURSEMENT_RATIO,
        item_breakdowns=breakdowns,
    )


def upload_expenses(payload: ExpenseUploadRequest, principal: dict) -> ExpenseUploadResponse:
    item_codes = [item.item_code for item in payload.items]
    if len(item_codes) != len(set(item_codes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorMessages.DUPLICATED_ITEM)
    total = sum((item.amount for item in payload.items), Decimal("0.00"))
    return ExpenseUploadResponse(batch_no=f"UP{uuid4().hex[:12].upper()}", accepted_count=len(payload.items), total_amount=total)


def pre_settle(payload: PreSettlementRequest, principal: dict) -> PreSettlementResponse:
    calc = calculate_settlement(payload.items, payload.region, get_account_balance(payload.insured_id))
    return PreSettlementResponse(
        insured_id=payload.insured_id,
        region=payload.region,
        total_amount=calc.total_amount,
        reimbursable_base=calc.reimbursable_base,
        reimbursed_amount=calc.reimbursed_amount,
        account_pay_amount=calc.account_pay_amount,
        self_pay_amount=calc.self_pay_amount,
        account_balance=calc.account_balance,
        deductible=calc.deductible,
        reimbursement_ratio=calc.reimbursement_ratio,
        ratio_rule=RATIO_RULE,
        details=payload.items,
        item_breakdowns=calc.item_breakdowns,
    )


def confirm_settlement(payload: SettlementConfirmRequest, db: Session, principal: dict) -> SettlementResponse:
    # 正式结算按费用明细重新计算，与预结算保持同一口径，不直接信任调用方传入的金额
    calc = calculate_settlement(
        payload.pre_settlement.details,
        payload.pre_settlement.region,
        get_account_balance(payload.insured_id),
    )
    record = SettlementRecord(
        settlement_no=f"JS{uuid4().hex[:14].upper()}",
        batch_no=payload.batch_no,
        insured_id=payload.insured_id,
        total_amount=calc.total_amount,
        reimbursable_base=calc.reimbursable_base,
        reimbursed_amount=calc.reimbursed_amount,
        account_pay_amount=calc.account_pay_amount,
        self_pay_amount=calc.self_pay_amount,
        deductible=calc.deductible,
        reimbursement_ratio=calc.reimbursement_ratio,
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
