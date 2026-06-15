"""
Tests for opt-out handling across both the /optout endpoint and the worker.

The three cases we care about:
  1. A phone number on the opt-out list must be suppressed by the worker, not texted.
  2. Calling /optout twice for the same number must not crash or create duplicate rows.
  3. A phone number that is NOT on the opt-out list must still get sent normally.
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlmodel import Session, select

from app.models.db_models import ClientCampaign, OptOut, Tenant
from app.worker import process_pending_campaigns

pytestmark = pytest.mark.asyncio


def _make_campaign(tenant: Tenant, job_id: str, phone: str = "+15551234567") -> ClientCampaign:
    return ClientCampaign(
        tenant_id=tenant.id,
        customer_name="Opt-Out Test User",
        customer_phone=phone,
        provider="jobber",
        job_id=job_id,
        delivery_status="pending",
    )


async def test_opted_out_number_is_suppressed_not_sent(
    session: Session, test_tenant: Tenant
):
    """
    When a phone number is on the opt-out list, the worker must mark the campaign
    'suppressed' and must NOT call the SMS adapter at all.
    """
    phone = "+15550000001"

    # Add the phone to the opt-out list
    optout = OptOut(tenant_id=test_tenant.id, phone=phone)
    session.add(optout)

    # Create a pending campaign for that same phone number
    campaign = _make_campaign(test_tenant, "JOB-SUPPRESSED", phone=phone)
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=True)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "suppressed"
    assert campaign.retry_count == 0          # no send attempt, so no increment
    adapter.send_review_request.assert_not_called()


async def test_duplicate_optout_is_handled_gracefully(
    client: AsyncClient, session: Session, test_tenant: Tenant
):
    """
    POSTing the same phone number to /optout twice must return 200 both times
    and leave exactly one OptOut row in the database.
    """
    payload = {"phone": "+15550000002"}
    headers = {"X-Api-Key": test_tenant.api_key}

    first = await client.post("/api/v1/optout", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "opted_out"

    second = await client.post("/api/v1/optout", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "already_opted_out"

    rows = session.exec(
        select(OptOut).where(
            OptOut.tenant_id == test_tenant.id,
            OptOut.phone == "+15550000002",
        )
    ).all()
    assert len(rows) == 1


async def test_non_opted_out_number_still_sends(
    session: Session, test_tenant: Tenant
):
    """
    A phone number that is NOT on the opt-out list must be sent normally and
    the campaign marked 'sent'.
    """
    phone = "+15550000003"
    campaign = _make_campaign(test_tenant, "JOB-NORMAL-SEND", phone=phone)
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=True)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "sent"
    assert campaign.retry_count == 1

    expected_body = test_tenant.message_template.format(
        customer_name=campaign.customer_name,
        business_name=test_tenant.business_name,
        review_url=test_tenant.review_url,
    )
    adapter.send_review_request.assert_called_once_with(
        phone=phone,
        message_body=expected_body,
    )
