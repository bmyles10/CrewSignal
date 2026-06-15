"""
NOTES:
1. These are the blueprints for what gets saved in the database. Tenant is a roofing
   company (our paying customer). ClientCampaign is one job-completion event that is
   waiting for a review text to be sent. OptOut is a list of phone numbers that have
   asked not to receive any more texts.
2. IDs are long random strings (UUIDs) instead of counting numbers (1, 2, 3...). This
   stops anyone from guessing "what's record number 4?" and snooping on other tenants.
3. The index=True fields are like the tabs on a filing cabinet — they let the database
   jump straight to the right row instead of reading every single row from top to bottom.
4. The Relationship between Tenant and ClientCampaign lets us ask "show me all jobs for
   this roofing company" without writing any extra database code.
5. Each OptOut row is scoped to a tenant so one company's opt-outs don't affect another
   company's messages to the same phone number.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import UniqueConstraint

# The default SMS message every new tenant starts with.
# Supports three placeholders: {customer_name}, {business_name}, {review_url}.
# Tenants can override this with a custom template via manage.py.
DEFAULT_MESSAGE_TEMPLATE = (
    "Hi {customer_name}, thank you for choosing {business_name}! "
    "We'd love your feedback — please leave us a Google review here: {review_url} "
    "Reply STOP to opt out."
)


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
    message_template: str = Field(default=DEFAULT_MESSAGE_TEMPLATE)
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
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "job_id", name="uq_campaign_dedup"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)

    # Customer Details
    customer_name: str
    customer_phone: str = Field(index=True)

    # External CRM Identifiers (e.g., Jobber's internal Job ID number)
    provider: str = Field(default="jobber", index=True)
    job_id: str = Field(index=True)
    
    # Automated Dispatch State Tracker
    delivery_status: str = Field(default="pending")  # pending, sent, failed, duplicate, suppressed
    retry_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    # Link back up to the Parent Tenant profile
    tenant: Optional[Tenant] = Relationship(back_populates="campaigns")


class OptOut(SQLModel, table=True):
    """
    Suppression list. Any phone number in this table will never receive an SMS
    from the matching tenant, regardless of how many jobs are completed.
    """
    __tablename__: str = "opt_outs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="uq_optout_tenant_phone"),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    phone: str = Field(index=True)
    created_at: datetime = Field(default_factory=get_utc_now)