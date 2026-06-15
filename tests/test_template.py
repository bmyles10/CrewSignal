"""
Tests for per-tenant message template rendering and the update-tenant manage.py command.

Three cases:
  1. Template renders correctly when all three placeholders are present.
  2. A template with an unknown placeholder fails gracefully — campaign marked 'failed',
     adapter is never called.
  3. update-tenant (do_update_tenant helper) updates only the fields you pass in.
"""

import pytest
from unittest.mock import AsyncMock
from sqlmodel import Session

from app.models.db_models import ClientCampaign, Tenant, DEFAULT_MESSAGE_TEMPLATE
from app.worker import process_pending_campaigns
from manage import do_update_tenant


def _make_campaign(tenant: Tenant, job_id: str) -> ClientCampaign:
    return ClientCampaign(
        tenant_id=tenant.id,
        customer_name="Template Test User",
        customer_phone="+15559990000",
        provider="jobber",
        job_id=job_id,
        delivery_status="pending",
    )


@pytest.mark.asyncio
async def test_template_renders_correctly_with_all_variables(
    session: Session, test_tenant: Tenant
):
    """
    The worker must produce the correct message body by substituting all three
    placeholders from the tenant's message_template.
    """
    campaign = _make_campaign(test_tenant, "JOB-TEMPLATE-OK")
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=True)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "sent"

    expected_body = DEFAULT_MESSAGE_TEMPLATE.format(
        customer_name="Template Test User",
        business_name=test_tenant.business_name,
        review_url=test_tenant.review_url,
    )
    adapter.send_review_request.assert_called_once_with(
        phone=campaign.customer_phone,
        message_body=expected_body,
    )


@pytest.mark.asyncio
async def test_bad_placeholder_in_template_fails_gracefully(
    session: Session, test_tenant: Tenant
):
    """
    If the tenant's message_template contains an unknown placeholder, the worker
    must mark the campaign 'failed' and must NOT call the SMS adapter at all.
    """
    test_tenant.message_template = "Hello {customer_name}, call us at {typo_field}!"
    session.add(test_tenant)
    session.commit()

    campaign = _make_campaign(test_tenant, "JOB-BAD-TEMPLATE")
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=True)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "failed"
    adapter.send_review_request.assert_not_called()


def test_update_tenant_updates_correct_fields(session: Session, test_tenant: Tenant):
    """
    do_update_tenant must update the fields you pass and leave untouched fields alone.
    """
    original_name = test_tenant.business_name
    new_url = "https://g.page/new-roofing/review"
    new_template = "Hey {customer_name}, rate {business_name}: {review_url}"

    updated = do_update_tenant(
        session,
        test_tenant,
        review_url=new_url,
        message_template=new_template,
    )

    assert updated.review_url == new_url
    assert updated.message_template == new_template
    assert updated.business_name == original_name  # untouched

    # Verify the DB row was actually committed
    session.expire(updated)
    session.refresh(updated)
    assert updated.review_url == new_url
    assert updated.message_template == new_template


def test_update_tenant_partial_update_leaves_other_field_alone(
    session: Session, test_tenant: Tenant
):
    """
    Passing only review_url must not clobber message_template, and vice-versa.
    """
    original_template = test_tenant.message_template
    new_url = "https://g.page/partial-update/review"

    updated = do_update_tenant(session, test_tenant, review_url=new_url)

    assert updated.review_url == new_url
    assert updated.message_template == original_template
