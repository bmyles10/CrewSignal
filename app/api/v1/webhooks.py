"""
NOTES:
1. Fast Response: Webhooks should always return a 2xx status code immediately so the sending CRM doesn't timeout. We use status_code=202 (Accepted).
2. Dependency Injection: We inject `session: Session = Depends(get_session)` so FastAPI handles the database connection lifecycle safely.
3. Background Tasks: We inject FastAPI's BackgroundTasks. This lets us fire the SMS adapter completely asynchronously AFTER the 202 response is sent, preventing network latency from blocking the API thread.
4. Basic Payload: We are using a temporary basic Pydantic model here. We will enforce strict sanitization in Task 11.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.db import get_session
from app.models.db_models import ClientCampaign
from app.adapters.sms_mock import MockSMSAdapter

router = APIRouter()

class BasicJobberPayload(BaseModel):
    """Temporary schema to catch the webhook until we lock down sanitization in Task 11."""
    job_id: str
    customer_name: str
    customer_phone: str
    tenant_id: str 

@router.post("/job-completed", status_code=202)
async def process_job_completed(
    payload: BasicJobberPayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Receives the job completion signal from the field CRM, logs it to the database,
    and dispatches the review text in the background.
    """
    # Idempotency: return 202 immediately if this event was already processed
    existing = session.exec(
        select(ClientCampaign).where(
            ClientCampaign.tenant_id == payload.tenant_id,
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

    # Create a new campaign entry in our tracking database
    new_campaign = ClientCampaign(
        tenant_id=payload.tenant_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        provider="jobber",
        job_id=payload.job_id,
        delivery_status="pending"
    )

    session.add(new_campaign)
    session.commit()
    session.refresh(new_campaign)

    # Instantiate the local development mock adapter
    sms_adapter = MockSMSAdapter()

    # Generate a dummy review URL for testing (we will query the real one from the DB later)
    dummy_review_url = f"https://crewsignal.com/reviews/{payload.tenant_id}"

    # Fire the text message into the background queue so the API responds instantly
    background_tasks.add_task(
        sms_adapter.send_review_request,
        phone=payload.customer_phone,
        customer_name=payload.customer_name,
        review_url=dummy_review_url
    )

    return {
        "status": "accepted",
        "message": "Job completion logged and SMS dispatched.",
        "campaign_id": new_campaign.id,
    }