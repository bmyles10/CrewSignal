"""
NOTES:
1. This endpoint acts like a receptionist. When a job-completion event arrives, it
   writes it down and immediately says "got it, thanks!" — it doesn't make the CRM
   wait around while a text message is being sent. The actual texting happens later
   in the background worker.
2. We figure out which roofing company sent the request from their API key, not from
   anything inside the payload. The payload could be faked — the key can be checked
   against the database.
3. Before saving anything, we check if we've already seen this exact job ID from this
   company. CRMs often send the same event multiple times when they don't get an
   instant reply, so without this check the customer would get spammed with texts.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

from app.api.deps import get_current_tenant
from app.core.db import get_session
from app.models.db_models import ClientCampaign, Tenant

router = APIRouter()


class BasicJobberPayload(BaseModel):
    """Temporary schema to catch the webhook until we lock down sanitization in Task 11."""
    job_id: str
    customer_name: str
    customer_phone: str


@router.post("/job-completed", status_code=202)
async def process_job_completed(
    payload: BasicJobberPayload,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Writes the job event to the tracking ledger as 'pending' and returns 202
    immediately. The durable worker in app/worker.py handles SMS dispatch.
    """
    existing = session.exec(
        select(ClientCampaign).where(
            ClientCampaign.tenant_id == tenant.id,
            ClientCampaign.provider == "jobber",
            ClientCampaign.job_id == payload.job_id,
        )
    ).first()

    if existing:
        return {
            "status": "duplicate",
            "message": "Event already processed.",
            "campaign_id": existing.id,
        }

    new_campaign = ClientCampaign(
        tenant_id=tenant.id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        provider="jobber",
        job_id=payload.job_id,
        delivery_status="pending",
    )

    session.add(new_campaign)
    session.commit()
    session.refresh(new_campaign)

    return {
        "status": "accepted",
        "message": "Job completion logged. SMS queued for dispatch.",
        "campaign_id": new_campaign.id,
    }