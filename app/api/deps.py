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
