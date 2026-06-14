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
            f"If you have a minute, we'd love a quick review of our work: {review_url}"
        )
        try:
            self._send(phone, message_body)
            return True
        except Exception:
            return False
