"""
NOTES:
1. Quick Peek: This is a standalone diagnostic script to view the database content directly from PowerShell without installing an external GUI.
2. Direct Execution: Run this file with `python peek_db.py` to print out all logged webhook campaigns.
"""

from sqlmodel import Session, select
from app.core.db import engine
from app.models.db_models import ClientCampaign

def peek_ledger():
    print("\n" + "="*60)
    print(" 📊 [DATABASE LEDGER PEEK] - CURRENT LOGGED CAMPAIGNS")
    print("="*60)
    
    with Session(engine) as session:
        # Select all records from the client_campaigns table
        statement = select(ClientCampaign)
        results = session.exec(statement).all()
        
        if not results:
            print(" Ledger is currently empty. Run a webhook test in Swagger!")
        
        for campaign in results:
            print(f"ID: {campaign.id[:8]}... | Tenant: {campaign.tenant_id} | Phone: {campaign.customer_phone} | Status: {campaign.delivery_status}")
            
    print("="*60 + "\n")

if __name__ == "__main__":
    peek_ledger()