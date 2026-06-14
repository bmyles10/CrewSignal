"""
NOTES:
1. This is the front door of the whole app. It starts the web server, makes sure the
   database tables exist, and kicks off the background worker that sends text messages.
2. The lifespan block is like an opening and closing routine for a shop — setup code
   runs before the server lets anyone in, and cleanup code runs when it shuts down.
3. The background worker starts at the same time as the web server and quietly checks
   for pending texts every 10 seconds without getting in the way of incoming requests.
4. CORS is set to allow requests from anywhere right now so local testing is easy.
   Before going live, change allow_origins to only the CRM's domain so random websites
   can't poke the API.
5. reload=True means Uvicorn watches your files and restarts automatically when you
   save a change — no need to stop and rerun the server during development.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import create_db_and_tables
from app.worker import worker_loop

from app.api.v1 import optout, webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(" [SYSTEM] Initializing Database Ledgers...")
    create_db_and_tables()
    worker_task = asyncio.create_task(worker_loop())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

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

app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])
app.include_router(optout.router, prefix=f"{settings.API_V1_STR}", tags=["Opt-Out"])

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