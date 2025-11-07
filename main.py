from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routes import router

app = FastAPI(
    title="WhatsApp Automation API",
    description="Multi-account WhatsApp automation with agents",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["automation"])

@app.get("/")
async def root():
    return {
        "message": "WhatsApp Automation API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.on_event("shutdown")
async def shutdown():
    from manager import session_manager
    for sid in list(session_manager.sessions.keys()):
        session_manager.delete_session(sid)