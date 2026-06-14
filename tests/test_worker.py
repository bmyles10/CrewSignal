"""
Tests for the durable worker loop (app/worker.py).

We call process_pending_campaigns() directly and hand it a fake SMS sender, so
tests run instantly without needing a running server and without sending any real
texts to anyone.
"""

import pytest
from unittest.mock import AsyncMock
from sqlmodel import Session, select

from app.models.db_models import ClientCampaign, Tenant
from app.worker import process_pending_campaigns

pytestmark = pytest.mark.asyncio


def _make_campaign(tenant: Tenant, job_id: str, status: str = "pending") -> ClientCampaign:
    return ClientCampaign(
        tenant_id=tenant.id,
        customer_name="Worker Test User",
        customer_phone="+15551234567",
        provider="jobber",
        job_id=job_id,
        delivery_status=status,
    )


async def test_worker_sends_pending_rows_and_marks_sent(
    session: Session, test_tenant: Tenant
):
    """
    A pending campaign whose adapter call succeeds must be marked 'sent',
    have retry_count incremented, and have updated_at refreshed.
    """
    campaign = _make_campaign(test_tenant, "JOB-WORKER-SENT")
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=True)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "sent"
    assert campaign.retry_count == 1

    adapter.send_review_request.assert_called_once_with(
        phone=campaign.customer_phone,
        customer_name=campaign.customer_name,
        review_url=test_tenant.review_url,
    )


async def test_worker_marks_failed_when_adapter_returns_false(
    session: Session, test_tenant: Tenant
):
    """
    A pending campaign whose adapter call returns False must be marked 'failed'
    with retry_count incremented.
    """
    campaign = _make_campaign(test_tenant, "JOB-WORKER-FAIL")
    session.add(campaign)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock(return_value=False)

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(campaign)
    assert campaign.delivery_status == "failed"
    assert campaign.retry_count == 1


async def test_worker_skips_non_pending_rows(
    session: Session, test_tenant: Tenant
):
    """
    Campaigns already in 'sent', 'failed', or 'duplicate' status must not be
    touched — the adapter must not be called for them at all.
    """
    sent = _make_campaign(test_tenant, "JOB-ALREADY-SENT", status="sent")
    failed = _make_campaign(test_tenant, "JOB-ALREADY-FAILED", status="failed")
    duplicate = _make_campaign(test_tenant, "JOB-ALREADY-DUPE", status="duplicate")
    session.add(sent)
    session.add(failed)
    session.add(duplicate)
    session.commit()

    adapter = AsyncMock()
    adapter.send_review_request = AsyncMock()

    await process_pending_campaigns(session, adapter=adapter)

    adapter.send_review_request.assert_not_called()

    session.refresh(sent)
    session.refresh(failed)
    session.refresh(duplicate)
    assert sent.delivery_status == "sent"
    assert failed.delivery_status == "failed"
    assert duplicate.delivery_status == "duplicate"


async def test_worker_continues_after_per_row_exception(
    session: Session, test_tenant: Tenant
):
    """
    An exception on one row must not stop the worker from processing
    subsequent rows — the good row is marked 'sent', bad row stays 'pending'.
    """
    bad = _make_campaign(test_tenant, "JOB-BOOM")
    good = _make_campaign(test_tenant, "JOB-OK")
    session.add(bad)
    session.add(good)
    session.commit()

    call_count = 0

    async def flaky_send(phone, customer_name, review_url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated transient error")
        return True

    adapter = AsyncMock()
    adapter.send_review_request = flaky_send

    await process_pending_campaigns(session, adapter=adapter)

    session.refresh(bad)
    session.refresh(good)
    assert bad.delivery_status == "pending"   # untouched after exception
    assert good.delivery_status == "sent"
    assert call_count == 2
