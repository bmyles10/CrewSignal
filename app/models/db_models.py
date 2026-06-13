"""
NOTES:
1. SQLModel Relationship Mapping: We are utilizing SQLModel's native Relationship attribute. This allows us to lazily load a tenant's historical dispatches instantly without writing manual SQL JOIN queries.
2. Indexing Strategy: Indexes are explicitly added to `api_key` on the Tenant model and `job_id` on the ClientCampaign model. This guarantees sub-millisecond lookup speeds when the webhook gate processes high-volume incoming payloads.
3. UUID/String Primary Keys: Primary keys are typed as strings but default to standard UUID generation to prevent malicious sequential enumeration scanning of our database endpoints.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlmodel import Field, Relationship, SQLModel

def get_utc_now() -> datetime:
    """Helper to ensure all database entries use a standardized timezone-aware UTC format."""
    return datetime.now(timezone.utc)

class Tenant(SQLModel, table=True):
    """
    Represents an isolated corporate client (e.g., Rutherford Roofing) 
    authorized to route webhook events through CrewSignal.
    """
    __tablename__: str = "tenants"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    business_name: str = Field(index=True)
    api_key: str = Field(unique=True, index=True)
    review_url: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_utc_now)

    # Relationship link back to all messages sent by this specific business
    campaigns: List["ClientCampaign"] = Relationship(back_populates="tenant")


class ClientCampaign(SQLModel, table=True):
    """
    The transactional core log. Tracks individual job notifications, 
    customer contacts, and dispatch delivery states.
    """
    __tablename__: str = "client_campaigns"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    
    # Customer Details
    customer_name: str
    customer_phone: str = Field(index=True)
    
    # External CRM Identifiers (e.g., Jobber's internal Job ID number)
    job_id: str = Field(index=True)
    
    # Automated Dispatch State Tracker
    delivery_status: str = Field(default="pending")  # pending, sent, failed, duplicate
    retry_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    # Link back up to the Parent Tenant profile
    tenant: Optional[Tenant] = Relationship(back_populates="campaigns")