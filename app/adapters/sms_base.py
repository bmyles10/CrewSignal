"""
NOTES:
1. Abstract Base Classes (ABC): By inheriting from ABC and using @abstractmethod, we mathematically guarantee that any future adapter (like Twilio, Plivo, or AWS SNS) MUST implement `send_review_request` with the exact same arguments, or the server will crash on boot.
2. Async Signatures: We force the signature to be asynchronous so network calls never block the main FastAPI thread.
"""

from abc import ABC, abstractmethod

class BaseSMSAdapter(ABC):
    """
    The strict architectural contract for all outbound SMS communications.
    """
    
    @abstractmethod
    async def send_review_request(self, phone: str, customer_name: str, review_url: str) -> bool:
        """
        Dispatches the standard review request template to a customer.
        Must return True on successful delivery acknowledgement, False otherwise.
        """
        pass