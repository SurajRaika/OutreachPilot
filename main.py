from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routes import router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

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








ui_path = os.path.join(os.path.dirname(__file__), "ui")

if os.path.exists(ui_path):
    app.mount("/ui", StaticFiles(directory=ui_path), name="ui")

    @app.get("/ui", include_in_schema=False)
    async def serve_ui():
        """Serve the UI's main HTML file"""
        return FileResponse(os.path.join(ui_path, "index.html"))
else:
    print("⚠️ UI folder not found. Skipping UI mount.")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/index.html")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.on_event("shutdown")
async def shutdown():
    from manager import session_manager
    for sid in list(session_manager.sessions.keys()):
        session_manager.stop_session(sid)