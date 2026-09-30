from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default=PaymentStatus.PENDING.value)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    reference: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )