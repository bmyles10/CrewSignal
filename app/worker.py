"""
NOTES:
1. Think of this as a mail sorter who checks the inbox every 10 seconds. Any envelopes
   marked "pending" get picked up, sent out, and then marked "sent" or "failed".
2. We don't send the SMS inside the webhook because if the server restarts at the wrong
   moment the text would just disappear forever. Writing "pending" to the database first
   means the worker will always find it and try again after the server comes back up.
3. Before sending any text, the sorter checks a "do not mail" list (the OptOut table).
   If the customer's phone number is on that list, the campaign is marked "suppressed"
   and the text is never sent — no retry, no error, just quietly skipped.
4. The worker fills in the tenant's message template here, not inside the SMS adapter.
   That way each roofing company can have a custom message and the adapter just sends
   whatever string it's handed. If the template has a typo in a placeholder, the
   campaign is marked "failed" right here so the operator knows to fix it.
5. If one envelope causes an error (e.g. a bad phone number), the sorter logs the
   problem and moves on to the next one — it doesn't stop and refuse to deliver
   everything else.
6. Each check of the inbox opens a fresh database connection and closes it when done.
   This keeps the connection clean and avoids any leftover state from the previous run.
7. Tests can hand in a fake SMS sender directly, so we never accidentally call Twilio
   during a test run and we don't need to mess with any global settings to do it.
"""

import asyncio
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.adapters.sms_base import BaseSMSAdapter
from app.core.config import settings
from app.core.db import engine
from app.models.db_models import ClientCampaign, OptOut, Tenant

POLL_INTERVAL_SECONDS = 10


def _get_adapter() -> BaseSMSAdapter:
    if settings.USE_MOCK_SMS:
        from app.adapters.sms_mock import MockSMSAdapter
        return MockSMSAdapter()
    from app.adapters.sms_twilio import TwilioSMSAdapter
    return TwilioSMSAdapter()


async def process_pending_campaigns(
    session: Session,
    adapter: BaseSMSAdapter | None = None,
) -> None:
    """
    Single poll cycle. Fetches every 'pending' ClientCampaign, attempts to
    send the review-request SMS, and writes the result back to the row.

    Accepts an explicit adapter so tests can inject a mock without patching.
    """
    if adapter is None:
        adapter = _get_adapter()

    pending = session.exec(
        select(ClientCampaign).where(ClientCampaign.delivery_status == "pending")
    ).all()

    for campaign in pending:
        try:
            tenant = session.exec(
                select(Tenant).where(Tenant.id == campaign.tenant_id)
            ).first()

            if not tenant:
                continue

            opted_out = session.exec(
                select(OptOut).where(
                    OptOut.tenant_id == campaign.tenant_id,
                    OptOut.phone == campaign.customer_phone,
                )
            ).first()

            if opted_out:
                campaign.delivery_status = "suppressed"
                campaign.updated_at = datetime.now(timezone.utc)
                session.add(campaign)
                session.commit()
                continue

            try:
                message_body = tenant.message_template.format(
                    customer_name=campaign.customer_name,
                    business_name=tenant.business_name,
                    review_url=tenant.review_url,
                )
            except (KeyError, ValueError) as exc:
                print(f"[WORKER] Template rendering failed for campaign {campaign.id}: {exc}")
                campaign.delivery_status = "failed"
                campaign.updated_at = datetime.now(timezone.utc)
                session.add(campaign)
                session.commit()
                continue

            success = await adapter.send_review_request(
                phone=campaign.customer_phone,
                message_body=message_body,
            )

            campaign.delivery_status = "sent" if success else "failed"
            campaign.retry_count += 1
            campaign.updated_at = datetime.now(timezone.utc)
            session.add(campaign)
            session.commit()

        except Exception as exc:
            print(f"[WORKER] Error processing campaign {campaign.id}: {exc}")


async def worker_loop() -> None:
    """Durable polling loop. Runs forever, polling every POLL_INTERVAL_SECONDS seconds."""
    print("[WORKER] Durable SMS dispatch worker started.")
    while True:
        try:
            with Session(engine) as session:
                await process_pending_campaigns(session)
        except Exception as exc:
            print(f"[WORKER] Unexpected error in poll cycle: {exc}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
