"""
Tests for TwilioSMSAdapter.

We swap out the real Twilio Client with a fake one so no actual texts are ever sent
and no money is spent. We also freeze time.sleep so the retry waits happen instantly
instead of making the test suite take several minutes.
"""

import pytest
from unittest.mock import MagicMock, patch

from twilio.base.exceptions import TwilioRestException

from app.adapters.sms_twilio import TwilioSMSAdapter
from app.core.config import settings

pytestmark = pytest.mark.asyncio

_PHONE = "+15551234567"
_MESSAGE_BODY = (
    "Hi Jane Homeowner, thank you for choosing Test Roofing Co! "
    "We'd love your feedback — please leave us a Google review here: "
    "https://g.page/test-roofing/review Reply STOP to opt out."
)

# A canned TwilioRestException that represents any transient server error
_TRANSIENT_ERROR = TwilioRestException(status=500, uri="/2010-04-01/Accounts/x/Messages.json")


async def test_successful_send():
    """Adapter returns True and calls messages.create exactly once on a clean send."""
    with patch("app.adapters.sms_twilio.Client") as mock_client_cls, \
         patch("time.sleep"):
        mock_create = mock_client_cls.return_value.messages.create
        mock_create.return_value = MagicMock(sid="SM_SUCCESS")

        adapter = TwilioSMSAdapter()
        result = await adapter.send_review_request(_PHONE, _MESSAGE_BODY)

    assert result is True
    mock_create.assert_called_once_with(
        body=_MESSAGE_BODY,
        from_=settings.TWILIO_FROM_NUMBER,
        to=_PHONE,
    )


async def test_retries_on_transient_error():
    """
    Adapter retries after a TwilioRestException and returns True once it succeeds.
    Simulates two transient failures followed by a successful third attempt.
    """
    with patch("app.adapters.sms_twilio.Client") as mock_client_cls, \
         patch("time.sleep"):
        mock_create = mock_client_cls.return_value.messages.create
        mock_create.side_effect = [
            _TRANSIENT_ERROR,
            _TRANSIENT_ERROR,
            MagicMock(sid="SM_RETRY_OK"),
        ]

        adapter = TwilioSMSAdapter()
        result = await adapter.send_review_request(_PHONE, _MESSAGE_BODY)

    assert result is True
    assert mock_create.call_count == 3


async def test_failure_after_all_retries_exhausted():
    """
    Adapter returns False after the initial attempt plus all 3 retries fail
    (4 total calls to messages.create).
    """
    with patch("app.adapters.sms_twilio.Client") as mock_client_cls, \
         patch("time.sleep"):
        mock_create = mock_client_cls.return_value.messages.create
        mock_create.side_effect = _TRANSIENT_ERROR

        adapter = TwilioSMSAdapter()
        result = await adapter.send_review_request(_PHONE, _MESSAGE_BODY)

    assert result is False
    assert mock_create.call_count == 4  # 1 original + 3 retries


async def test_non_twilio_exception_is_not_retried():
    """
    A non-Twilio exception (e.g., network misconfiguration) must NOT trigger
    retries — it propagates immediately and the adapter returns False after 1 call.
    """
    with patch("app.adapters.sms_twilio.Client") as mock_client_cls, \
         patch("time.sleep"):
        mock_create = mock_client_cls.return_value.messages.create
        mock_create.side_effect = ConnectionError("DNS failure")

        adapter = TwilioSMSAdapter()
        result = await adapter.send_review_request(_PHONE, _MESSAGE_BODY)

    assert result is False
    assert mock_create.call_count == 1  # no retries for non-Twilio errors
