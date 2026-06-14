"""
NOTES:
1. Each test gets its own empty database that only exists while that test is running.
   When the test finishes, the database is completely deleted — so tests can never mess
   each other up by leaving leftover data behind.
2. We trick FastAPI into using the test database instead of the real one by swapping
   out the get_session function. The app thinks it's talking to production but it's
   actually using our throwaway test database.
3. The httpx client lets us send fake HTTP requests directly to the app without
   starting a real web server — tests run fast and nothing hits the network.
4. test_tenant creates a fake roofing company in the test database before each test so
   the API key check has something real to look up. Any test that calls the webhook
   needs this.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

# Import your FastAPI app and database dependency
from main import app
from app.core.db import get_session
from app.models.db_models import Tenant

# 1. Create a lightning-fast in-memory database for testing
sqlite_url = "sqlite://"
test_engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    """Builds a fresh database schema for every single test and tears it down after."""
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest_asyncio.fixture(name="client")
async def client_fixture(session: Session):
    """Overrides the live API dependencies to route traffic to the test database."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="test_tenant")
def test_tenant_fixture(session: Session) -> Tenant:
    """Inserts a reusable Tenant row for auth tests."""
    tenant = Tenant(
        business_name="Test Roofing Co",
        api_key="test-api-key-abc123",
        review_url="https://g.page/test-roofing/review",
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant