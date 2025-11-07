from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

from routes import router

# Environment variables
SECRET = os.getenv("SECRET", "default-secret")

# Initialize FastAPI app
app = FastAPI(
    title="Automation Session API",
    description="API for managing WhatsApp and web automation sessions",
    version="1.0.0"
)

# CORS middleware for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api", tags=["automation"])

# Basic routes
@app.get("/")
async def root():
    return {
        "message": "Automation Session API",
        "version": "1.0.0",
        "endpoints": {
            "sessions": "/api/sessions",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    from manager import session_manager
    for session_id in list(session_manager.sessions.keys()):
        session_manager.delete_session(session_id)