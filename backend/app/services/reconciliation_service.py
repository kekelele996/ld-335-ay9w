from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settlement import SettlementRecord


def daily_summary(day: date, db: Session, principal: dict) -> dict:
    start_at = datetime.combine(day, time.min)
    end_at = datetime.combine(day, time.max)
    records = db.scalars(
        select(SettlementRecord).where(
            SettlementRecord.created_at >= start_at,
            SettlementRecord.created_at <= end_at,
        )
    ).all()
    # 金额口径与预结算/正式结算一致：总额 = 医保报销 + 个人账户支付 + 个人自费
    total_amount = sum((record.total_amount for record in records), Decimal("0.00"))
    total_reimbursed = sum((record.reimbursed_amount for record in records), Decimal("0.00"))
    total_account_pay = sum((record.account_pay_amount for record in records), Decimal("0.00"))
    total_self_pay = sum((record.self_pay_amount for record in records), Decimal("0.00"))
    success_count = sum(1 for record in records if record.status == "SUCCESS")
    reversed_count = sum(1 for record in records if record.status == "REVERSED")
    failed_count = sum(1 for record in records if record.status not in {"SUCCESS", "REVERSED"})
    return {
        "day": day.isoformat(),
        "total_count": len(records),
        "success_count": success_count,
        "failed_count": failed_count,
        "reversed_count": reversed_count,
        "total_amount": str(total_amount),
        "total_reimbursed_amount": str(total_reimbursed),
        "total_account_pay_amount": str(total_account_pay),
        "total_self_pay_amount": str(total_self_pay),
        "manual_review_count": failed_count,
    }
