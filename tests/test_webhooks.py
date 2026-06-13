"""
NOTES:
1. Async Execution: We use @pytest.mark.asyncio because our FastAPI app and httpx client are fully asynchronous.
2. Tag Standardization: Applied standard @pytest.mark.new_test for suite filtering.
3. E2E Verification: We don't just check the 202 status code; we actually query the test database session to physically prove the row was inserted correctly.
"""

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models.db_models import ClientCampaign

# Standardize tags for the entire file
pytestmark = [pytest.mark.asyncio, pytest.mark.new_test]

async def test_job_completed_webhook_creates_campaign(client: AsyncClient, session: Session):
    """
    Test that a valid CRM webhook payload successfully logs a new campaign
    in the tracking ledger and returns a 202 Accepted status.
    """
    # 1. Define the test payload (Simulating Jobber CRM)
    payload = {
        "job_id": "JOB-9999",
        "customer_name": "Test User",
        "customer_phone": "+15551234567",
        "tenant_id": "TENANT-123"
    }
    
    # 2. Fire the simulated webhook at the gateway
    response = await client.post("/api/v1/webhooks/job-completed", json=payload)
    
    # 3. Assert the API responded correctly
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "campaign_id" in data
    
    # 4. Assert the database physically saved the record inside the isolated test session
    statement = select(ClientCampaign).where(ClientCampaign.job_id == "JOB-9999")
    db_record = session.exec(statement).first()
    
    assert db_record is not None
    assert db_record.customer_name == "Test User"
    assert db_record.delivery_status == "pending"