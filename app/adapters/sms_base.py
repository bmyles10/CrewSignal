"""
NOTES:
1. This file is a job description, not actual code. It says "any SMS sender we ever
   build must have a method called send_review_request that takes these exact inputs
   and returns True or False". If someone builds a new sender and forgets that method,
   Python will refuse to run it at all.
2. The method is async so the rest of the app doesn't have to sit and wait while a
   text message is being sent out — it can keep handling other requests in the meantime.
"""

from abc import ABC, abstractmethod

class BaseSMSAdapter(ABC):
    """
    The strict architectural contract for all outbound SMS communications.
    """
    
    @abstractmethod
    async def send_review_request(self, phone: str, message_body: str) -> bool:
        """
        Sends a pre-rendered SMS message to the given phone number.
        The caller is responsible for building the message body before calling this.
        Must return True on successful delivery acknowledgement, False otherwise.
        """
        pass