"""
NOTES:
1. This is the receiving end for texts customers send back to your Twilio number —
   most importantly "STOP". Twilio calls this URL directly, so there's no X-Api-Key
   header to check. Instead we verify the request really came from Twilio using their
   signature scheme (HMAC over the URL + form body, signed with your Auth Token).
2. Because one Twilio number is currently shared across tenants, we figure out *which*
   roofing company this customer belongs to by finding the most recent ClientCampaign
   sent to their phone number. That tells us whose suppression list to add them to.
3. If we can't find any campaign history for that phone number, we log it and do
   nothing — there's no tenant to attribute the opt-out to.
4. Any inbound text that isn't STOP (a wrong number, "thanks!", whatever) is just
   logged and ignored. We always return valid empty TwiML so Twilio doesn't retry
   or treat it as a delivery failure.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import Session, select
from twilio.request_validator import RequestValidator

from app.core.config import settings
from app.core.db import get_session
from app.models.db_models import ClientCampaign, OptOut

router = APIRouter()

_EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
_STOP_KEYWORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}


def _verify_twilio_signature(request: Request, form_data: dict) -> bool:
    if not settings.TWILIO_AUTH_TOKEN or settings.TWILIO_AUTH_TOKEN == "mock_token":
        return True  # local dev / mock mode — skip signature check

    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}{request.url.path}"
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, form_data, signature)


@router.post("/webhooks/twilio-inbound")
async def twilio_inbound_sms(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    session: Session = Depends(get_session),
):
    form_data = dict(await request.form())

    if not _verify_twilio_signature(request, form_data):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature.")

    body_normalized = Body.strip().lower()

    if body_normalized in _STOP_KEYWORDS:
        latest_campaign = session.exec(
            select(ClientCampaign)
            .where(ClientCampaign.customer_phone == From)
            .order_by(ClientCampaign.created_at.desc())
        ).first()

        if latest_campaign:
            existing = session.exec(
                select(OptOut).where(
                    OptOut.tenant_id == latest_campaign.tenant_id,
                    OptOut.phone == From,
                )
            ).first()

            if not existing:
                session.add(OptOut(tenant_id=latest_campaign.tenant_id, phone=From))
                session.commit()
                print(f"[INBOUND] {From} opted out of tenant {latest_campaign.tenant_id}")
        else:
            print(f"[INBOUND] STOP received from {From} but no campaign history found — could not attribute to a tenant.")
    else:
        print(f"[INBOUND] Non-STOP message from {From}: {Body!r}")

    return Response(content=_EMPTY_TWIML, media_type="application/xml")
