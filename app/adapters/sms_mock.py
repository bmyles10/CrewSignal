"""
NOTES:
1. Simulated Latency: We use asyncio.sleep(1) to simulate the time it takes to handshake with a real telecommunications carrier. This ensures our local testing accurately reflects production timing.
2. Formatted Output: The print statement uses a clean, multiline f-string to output a highly visible receipt directly into your PowerShell terminal so you can verify the exact phrasing the customer will see.
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
            f"If you have a minute, we'd love a quick review of our work: {review_url}"
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