import pytest
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models.db_models import ClientCampaign, Tenant

pytestmark = [pytest.mark.asyncio, pytest.mark.new_test]


async def test_job_completed_webhook_creates_campaign(
    client: AsyncClient, session: Session, test_tenant: Tenant
):
    """Valid API key + payload creates one campaign row and returns 202 accepted."""
    payload = {
        "job_id": "JOB-9999",
        "customer_name": "Test User",
        "customer_phone": "+15551234567",
    }

    response = await client.post(
        "/api/v1/webhooks/job-completed",
        json=payload,
        headers={"X-Api-Key": test_tenant.api_key},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "campaign_id" in data

    db_record = session.exec(
        select(ClientCampaign).where(ClientCampaign.job_id == "JOB-9999")
    ).first()
    assert db_record is not None
    assert db_record.tenant_id == test_tenant.id
    assert db_record.customer_name == "Test User"
    assert db_record.delivery_status == "pending"


async def test_duplicate_webhook_returns_202_without_double_insert(
    client: AsyncClient, session: Session, test_tenant: Tenant
):
    """Sending the same job_id twice returns 202 duplicate and creates only one row."""
    payload = {
        "job_id": "JOB-DUPE",
        "customer_name": "Dupe User",
        "customer_phone": "+15559876543",
    }
    headers = {"X-Api-Key": test_tenant.api_key}

    first = await client.post("/api/v1/webhooks/job-completed", json=payload, headers=headers)
    assert first.status_code == 202
    assert first.json()["status"] == "accepted"

    second = await client.post("/api/v1/webhooks/job-completed", json=payload, headers=headers)
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"

    rows = session.exec(
        select(ClientCampaign).where(ClientCampaign.job_id == "JOB-DUPE")
    ).all()
    assert len(rows) == 1


async def test_missing_api_key_returns_401(client: AsyncClient, test_tenant: Tenant):
    """Request without X-Api-Key header must be rejected with 401."""
    payload = {"job_id": "JOB-NOAUTH", "customer_name": "No Auth", "customer_phone": "+15550000000"}

    response = await client.post("/api/v1/webhooks/job-completed", json=payload)

    assert response.status_code == 401


async def test_invalid_api_key_returns_401(client: AsyncClient, test_tenant: Tenant):
    """Request with a wrong API key must be rejected with 401."""
    payload = {"job_id": "JOB-BADKEY", "customer_name": "Bad Key", "customer_phone": "+15550000001"}

    response = await client.post(
        "/api/v1/webhooks/job-completed",
        json=payload,
        headers={"X-Api-Key": "not-a-real-key"},
    )

    assert response.status_code == 401
