"""
NOTES:
1. This is a pretend SMS sender for local development. Instead of actually texting
   anyone and costing money, it just prints the message to your terminal so you can
   read exactly what the customer would receive.
2. The asyncio.sleep(1) fakes the small delay a real network call would take. This
   makes local testing feel like it behaves the same as production.
"""

import asyncio
from app.adapters.sms_base import BaseSMSAdapter

class MockSMSAdapter(BaseSMSAdapter):
    """
    A zero-cost, local development adapter that mimics telecommunication delivery
    by printing the formatted payload directly to the server terminal.
    """
    
    async def send_review_request(self, phone: str, customer_name: str, review_url: str) -> bool:
        # Simulate network latency to mimic a real Twilio API call
        await asyncio.sleep(1)
        
        # Format the exact message the customer would receive
        message_body = (
            f"Hi {customer_name}, thanks for choosing us! "
            f"If you have a minute, we'd love a quick review of our work: {review_url} "
            f"Reply STOP to opt out."
        )
        
        # Print the visual receipt to the terminal
        print("\n" + "="*50)
        print(" 📱 [MOCK SMS DISPATCHER] - MESSAGE DELIVERED")
        print("="*50)
        print(f" TO:      {phone}")
        print(f" MESSAGE: {message_body}")
        print("="*50 + "\n")
        
        # Return True to indicate successful mock delivery
        return True