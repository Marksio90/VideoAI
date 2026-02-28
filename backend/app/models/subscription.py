"""Model subskrypcji Stripe."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SubscriptionPlan(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    AGENCY = "agency"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


PLAN_LIMITS = {
    SubscriptionPlan.FREE: {"max_series": 1, "max_videos_per_month": 3},
    SubscriptionPlan.BASIC: {"max_series": 3, "max_videos_per_month": 15},
    SubscriptionPlan.PRO: {"max_series": 10, "max_videos_per_month": 60},
    SubscriptionPlan.AGENCY: {"max_series": 50, "max_videos_per_month": 300},
}


class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    plan: Mapped[str] = mapped_column(
        String(50), default=SubscriptionPlan.FREE, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=SubscriptionStatus.ACTIVE, nullable=False
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False)

    user = relationship("User", back_populates="subscriptions")
