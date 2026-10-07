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
    total_amount = sum((record.total_amount for record in records), Decimal("0.00"))
    reimbursed_amount = sum((record.reimbursed_amount for record in records), Decimal("0.00"))
    account_pay_amount = sum((record.account_pay_amount for record in records), Decimal("0.00"))
    self_pay_amount = sum((record.self_pay_amount for record in records), Decimal("0.00"))
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
        "reimbursed_amount": str(reimbursed_amount),
        "account_pay_amount": str(account_pay_amount),
        "self_pay_amount": str(self_pay_amount),
        "manual_review_count": failed_count,
    }
