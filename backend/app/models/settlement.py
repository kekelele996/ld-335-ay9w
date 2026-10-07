from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import business_now
from app.db.session import Base


class SettlementRecord(Base):
    __tablename__ = "settlement_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    settlement_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    batch_no: Mapped[str] = mapped_column(String(64), index=True)
    insured_id: Mapped[str] = mapped_column(String(32), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reimbursable_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reimbursed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    account_pay_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    self_pay_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deductible: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reimbursement_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=business_now)
