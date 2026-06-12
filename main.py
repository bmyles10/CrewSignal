"""
NOTES:
1. Uvicorn Reload: The reload=True flag inside the execution loop means you can leave this terminal running. Anytime we update a file, the server automatically reboots itself.
2. CORS Middleware: Currently configured permissively (allow_origins=["*"]) so external CRM webhooks can hit our local gateway during Phase 2 testing. We will lock this down in Phase 5.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Standard permissive CORS setup for local webhook testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    print(f" [STATUS] Health Check available at http://localhost:8000/health ")
    print("="*50)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)