"""
routers/billing.py — Billing infrastructure (Stripe-ready skeleton).

This module builds the complete billing data model and API surface.
Real Stripe integration is added by setting STRIPE_SECRET_KEY in .env
and wiring the checkout/webhook handlers below.

Plans:
  free       — 1,000 traces/month, 1 member, 30-day retention, $0
  pro        — 50,000 traces/month, 10 members, 90-day retention, $29/mo
  enterprise — unlimited traces, unlimited members, 365-day retention, $199/mo

Why build the skeleton before Stripe?
  The data model (subscriptions table, plan limits, usage counts) is
  pure backend work that doesn't need a payment processor. Building it
  now means the upgrade path is: add STRIPE_SECRET_KEY → uncomment
  checkout session creation → done. No schema migrations needed later.

Endpoints:
  GET  /billing/{project_id}           — current plan + usage this month
  POST /billing/{project_id}/upgrade   — change plan (mocked until Stripe wired)
  GET  /billing/plans                  — list all available plans
"""

import logging
import os

from auth.dependencies import require_role
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.audit import log_action

logger = logging.getLogger("swarmtrace.billing")

router = APIRouter(prefix="/billing", tags=["billing"])

# ── Plan definitions ──────────────────────────────────────────────────────────

PLANS: dict[str, dict] = {
    "free": {
        "name":             "Free",
        "price_usd":        0,
        "traces_per_month": 1_000,
        "max_members":      1,
        "retention_days":   30,
        "features": [
            "1,000 traces/month",
            "1 team member",
            "30-day retention",
            "WebSocket live streaming",
            "LLM-as-a-judge evals",
            "OTLP export",
        ],
    },
    "pro": {
        "name":             "Pro",
        "price_usd":        29,
        "traces_per_month": 50_000,
        "max_members":      10,
        "retention_days":   90,
        "features": [
            "50,000 traces/month",
            "10 team members",
            "90-day retention",
            "Everything in Free",
            "Webhook alerting",
            "Audit logs",
            "Priority support",
        ],
    },
    "enterprise": {
        "name":             "Enterprise",
        "price_usd":        199,
        "traces_per_month": None,   # unlimited
        "max_members":      None,   # unlimited
        "retention_days":   365,
        "features": [
            "Unlimited traces",
            "Unlimited team members",
            "365-day retention",
            "Everything in Pro",
            "RBAC (Admin/Developer/Viewer)",
            "Data retention controls",
            "SSO (coming soon)",
            "SLA guarantee",
        ],
    },
}

# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_SUBSCRIPTIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS subscriptions (
        sub_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id      UUID        UNIQUE REFERENCES projects(project_id) ON DELETE CASCADE,
        plan            VARCHAR(20) NOT NULL DEFAULT 'free',
        stripe_customer_id   VARCHAR(100),
        stripe_subscription_id VARCHAR(100),
        current_period_start TIMESTAMP,
        current_period_end   TIMESTAMP,
        status          VARCHAR(20) NOT NULL DEFAULT 'active',
        created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
    );
"""


async def ensure_subscriptions_table() -> None:
    """Create subscriptions table if it doesn't exist. Called at startup."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_SUBSCRIPTIONS_TABLE)

        # Seed free plan for existing projects that have no subscription yet
        await conn.execute("""
            INSERT INTO subscriptions (project_id, plan)
            SELECT project_id, 'free'
            FROM projects
            WHERE project_id NOT IN (SELECT project_id FROM subscriptions)
            ON CONFLICT DO NOTHING
        """)


# ── Usage helpers ─────────────────────────────────────────────────────────────

async def get_monthly_trace_count(project_id: str) -> int:
    """Count traces created this calendar month for a project."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM traces
            WHERE project_id = $1
              AND created_at >= DATE_TRUNC('month', NOW())
        """, project_id)
    return count or 0


async def check_trace_limit(project_id: str) -> dict:
    """
    Check if a project has hit its monthly trace limit.
    Returns {"allowed": bool, "used": int, "limit": int | None, "plan": str}

    Called by /ingest to enforce plan limits.
    Currently returns a warning — hard enforcement can be added when billing is live.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT plan FROM subscriptions WHERE project_id = $1
        """, project_id)

    plan_key = row["plan"] if row else "free"
    plan     = PLANS.get(plan_key, PLANS["free"])
    limit    = plan["traces_per_month"]
    used     = await get_monthly_trace_count(project_id)

    return {
        "allowed": limit is None or used < limit,
        "used":    used,
        "limit":   limit,
        "plan":    plan_key,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/plans")
async def list_plans():
    """Return all available plans. Public — no auth required."""
    return [
        {"plan_id": k, **v}
        for k, v in PLANS.items()
    ]


@router.get("/{project_id}")
async def get_billing(
    project_id: str,
    user: dict = Depends(require_role("project_id", "viewer")),  # noqa: B008
):
    """
    Return the current subscription and usage for a project.
    Any project member can view billing info.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        sub = await conn.fetchrow("""
            SELECT plan, status, stripe_customer_id,
                   current_period_start, current_period_end, updated_at
            FROM subscriptions
            WHERE project_id = $1
        """, project_id)

    if not sub:
        # Auto-create free plan if missing
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO subscriptions (project_id, plan)
                VALUES ($1, 'free')
                ON CONFLICT DO NOTHING
            """, project_id)
        plan_key = "free"
    else:
        plan_key = sub["plan"]

    plan  = PLANS.get(plan_key, PLANS["free"])
    used  = await get_monthly_trace_count(project_id)
    limit = plan["traces_per_month"]

    return {
        "project_id":    project_id,
        "plan":          plan_key,
        "plan_details":  plan,
        "status":        sub["status"] if sub else "active",
        "usage": {
            "traces_this_month": used,
            "traces_limit":      limit,
            "percent_used":      round(used / limit * 100, 1) if limit else 0,
        },
        "stripe_connected": bool(
            sub and sub["stripe_customer_id"]
        ),
        "period": {
            "start": sub["current_period_start"] if sub else None,
            "end":   sub["current_period_end"]   if sub else None,
        },
    }


class UpgradeRequest(BaseModel):
    plan: str  # "free" | "pro" | "enterprise"


@router.post("/{project_id}/upgrade")
async def upgrade_plan(
    project_id: str,
    body: UpgradeRequest,
    user: dict = Depends(require_role("project_id", "admin")),  # noqa: B008
):
    """
    Change the project's subscription plan.
    Requires admin.

    Currently MOCKED — records the plan change in the DB without
    charging a card. When Stripe is ready:
      1. Set STRIPE_SECRET_KEY in .env
      2. Create a Stripe checkout session here
      3. Return the checkout URL instead of the success response
      4. Handle the webhook in POST /billing/webhook (add below)
    """
    if body.plan not in PLANS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan '{body.plan}'. Valid plans: {', '.join(PLANS.keys())}",
        )

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key and stripe_key.startswith("sk_"):
        # TODO: Real Stripe integration when ready
        # import stripe
        # stripe.api_key = stripe_key
        # session = stripe.checkout.Session.create(...)
        # return {"checkout_url": session.url}
        logger.info("Stripe key present but checkout not yet wired — using mock upgrade")

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO subscriptions (project_id, plan)
            VALUES ($1, $2)
            ON CONFLICT (project_id) DO UPDATE
                SET plan       = EXCLUDED.plan,
                    updated_at = NOW()
        """, project_id, body.plan)

    plan_details = PLANS[body.plan]

    await log_action(
        project_id=project_id,
        user_id=user["user_id"],
        user_email=user["email"],
        action="PLAN_CHANGED",
        resource_type="project",
        resource_id=project_id,
        metadata={"new_plan": body.plan, "price_usd": plan_details["price_usd"]},
    )

    return {
        "project_id":   project_id,
        "plan":         body.plan,
        "plan_details": plan_details,
        "status":       "active",
        "message":      f"Plan updated to {plan_details['name']}. "
                        + ("Add STRIPE_SECRET_KEY to enable real payments." if not stripe_key else ""),
    }