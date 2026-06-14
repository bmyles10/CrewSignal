"""
NOTES:
1. This endpoint is how a customer removes themselves from future texts. When someone
   replies STOP to a message, the CRM can call this endpoint and we'll make sure they
   never get another text from that roofing company.
2. Calling this endpoint twice with the same phone number is fine — we check if they're
   already opted out and just say "yep, already done" instead of crashing.
3. Opt-outs are scoped to the tenant (roofing company) identified by the API key. One
   company opting out a number doesn't affect any other company's messages to that
   same number.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

from app.api.deps import get_current_tenant
from app.core.db import get_session
from app.models.db_models import OptOut, Tenant

router = APIRouter()


class OptOutPayload(BaseModel):
    phone: str


@router.post("/optout", status_code=200)
async def register_optout(
    payload: OptOutPayload,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Adds a phone number to the opt-out suppression list for the authenticated tenant.
    Safe to call multiple times for the same number.
    """
    existing = session.exec(
        select(OptOut).where(
            OptOut.tenant_id == tenant.id,
            OptOut.phone == payload.phone,
        )
    ).first()

    if existing:
        return {"status": "already_opted_out", "phone": payload.phone}

    optout = OptOut(tenant_id=tenant.id, phone=payload.phone)
    session.add(optout)
    session.commit()

    return {"status": "opted_out", "phone": payload.phone}
