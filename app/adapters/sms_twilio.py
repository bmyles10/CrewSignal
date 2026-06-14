"""
NOTES:
1. This is the real SMS sender that talks to Twilio, the company that actually delivers
   text messages to people's phones. We use their official Python library to make the
   call.
2. Networks aren't perfect. If Twilio returns an error, we automatically try again —
   first after 1 second, then 2 seconds, then 4 seconds. After 4 total attempts with
   no luck, we give up and return False so the worker can mark the row "failed".
3. We only retry on Twilio-specific errors. If something completely different goes wrong
   (like no internet connection at all), we stop immediately instead of waiting around.
4. The phone account credentials are loaded from the settings file, not typed directly
   into this file. That way they never accidentally end up in Git for the world to see.
"""

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.adapters.sms_base import BaseSMSAdapter
from app.core.config import settings


class TwilioSMSAdapter(BaseSMSAdapter):
    """Production SMS adapter — wraps the Twilio REST client with tenacity retry."""

    def __init__(self) -> None:
        self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    @retry(
        stop=stop_after_attempt(4),          # 1 initial attempt + 3 retries
        wait=wait_exponential(multiplier=1, min=1, max=30),  # 1 s → 2 s → 4 s
        retry=retry_if_exception_type(TwilioRestException),
        reraise=True,
    )
    def _send(self, to: str, body: str) -> None:
        self._client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to,
        )

    async def send_review_request(self, phone: str, customer_name: str, review_url: str) -> bool:
        message_body = (
            f"Hi {customer_name}, thanks for choosing us! "
            f"If you have a minute, we'd love a quick review of our work: {review_url} "
            f"Reply STOP to opt out."
        )
        try:
            self._send(phone, message_body)
            return True
        except Exception:
            return False
