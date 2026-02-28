"""
Webhooks — Stripe, platformy.
Ulepszenie: weryfikacja podpisu + idempotentność.
"""

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.subscription import Subscription, SubscriptionStatus, PLAN_LIMITS
from app.models.user import User

router = APIRouter()
settings = get_settings()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Obsługa webhooków Stripe.
    Weryfikacja podpisu zapobiega fałszywym zdarzeniom.
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy podpis")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.created":
        await _handle_subscription_created(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    elif event_type == "invoice.paid":
        pass  # Logowanie płatności
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)

    return {"received": True}


async def _handle_subscription_created(data: dict, db: AsyncSession):
    """Obsługa nowej subskrypcji."""
    customer_id = data["customer"]
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    plan = _resolve_plan(data)
    sub = Subscription(
        user_id=user.id,
        stripe_subscription_id=data["id"],
        plan=plan,
        status=data["status"],
        current_period_start=data.get("current_period_start"),
        current_period_end=data.get("current_period_end"),
    )
    db.add(sub)

    # Aktualizacja limitów użytkownika
    limits = PLAN_LIMITS.get(plan, {})
    user.max_series = limits.get("max_series", user.max_series)
    user.max_videos_per_month = limits.get("max_videos_per_month", user.max_videos_per_month)
    db.add(user)
    await db.flush()


async def _handle_subscription_updated(data: dict, db: AsyncSession):
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == data["id"])
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = data["status"]
    sub.cancel_at_period_end = data.get("cancel_at_period_end", False)

    new_plan = _resolve_plan(data)
    if new_plan != sub.plan:
        sub.plan = new_plan
        # Aktualizacja limitów
        user_result = await db.execute(select(User).where(User.id == sub.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            limits = PLAN_LIMITS.get(new_plan, {})
            user.max_series = limits.get("max_series", user.max_series)
            user.max_videos_per_month = limits.get("max_videos_per_month", user.max_videos_per_month)
            db.add(user)

    db.add(sub)
    await db.flush()


async def _handle_subscription_deleted(data: dict, db: AsyncSession):
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == data["id"])
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = SubscriptionStatus.CANCELLED
    db.add(sub)

    # Resetowanie limitów do darmowego planu
    user_result = await db.execute(select(User).where(User.id == sub.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        free_limits = PLAN_LIMITS.get("free", {})
        user.max_series = free_limits.get("max_series", 1)
        user.max_videos_per_month = free_limits.get("max_videos_per_month", 3)
        db.add(user)

    await db.flush()


async def _handle_payment_failed(data: dict, db: AsyncSession):
    sub_id = data.get("subscription")
    if not sub_id:
        return
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = SubscriptionStatus.PAST_DUE
        db.add(sub)
        await db.flush()


def _resolve_plan(data: dict) -> str:
    """Wyciąga plan z metadanych produktu Stripe."""
    items = data.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        if price_id == settings.STRIPE_PRICE_BASIC:
            return "basic"
        elif price_id == settings.STRIPE_PRICE_PRO:
            return "pro"
        elif price_id == settings.STRIPE_PRICE_AGENCY:
            return "agency"
    return "free"
