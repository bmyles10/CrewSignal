"""
NOTES:
1. Uvicorn Reload: The reload=True flag inside the execution loop means you can leave this terminal running.
2. CORS Middleware: Currently configured permissively for local testing.
3. Async Lifespan: We use FastAPI's @asynccontextmanager to ensure `create_db_and_tables()` runs before the server accepts any traffic.
4. Router Integration: Injected the v1 webhooks router to expose our /job-completed endpoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import create_db_and_tables

# Import the new webhooks router
from app.api.v1 import webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Boot sequence: Build the database tables before taking requests
    print(" [SYSTEM] Initializing Database Ledgers...")
    create_db_and_tables()
    yield
    # Shutdown sequence goes here if needed later

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # Attach the boot sequence
)

# Standard permissive CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire up the new endpoints
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Diagnostic endpoint to verify the CrewSignal gateway is active.
    """
    return {
        "status": "online", 
        "project": settings.PROJECT_NAME, 
        "message": "CrewSignal gateway is active and awaiting payloads."
    }

if __name__ == "__main__":
    import uvicorn
    print("="*50)
    print(f" [SYSTEM] Booting {settings.PROJECT_NAME} Webhook Gateway ")
    print("="*50)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)