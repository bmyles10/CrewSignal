"""
NOTES:
1. This is the bouncer at the door. Every request to the webhook must carry an
   X-Api-Key header. We look that key up in the database — if it matches an active
   roofing company, we let the request through and pass their info along.
2. We make the key optional (not required) because if it were required and someone
   forgot to send it, FastAPI would return a confusing "422" error. We want a clear
   "401 unauthorized" instead, which is the right message for a missing key.
3. A missing key and a wrong key both get the exact same error message. This means
   someone trying to guess keys can't tell which ones exist just by looking at the
   response.
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.db_models import Tenant

_UNAUTHORIZED = HTTPException(status_code=401, detail="Invalid or missing API key.")


async def get_current_tenant(
    x_api_key: Optional[str] = Header(None),
    session: Session = Depends(get_session),
) -> Tenant:
    if not x_api_key:
        raise _UNAUTHORIZED
    tenant = session.exec(
        select(Tenant).where(Tenant.api_key == x_api_key)
    ).first()
    if not tenant or not tenant.is_active:
        raise _UNAUTHORIZED
    return tenant
