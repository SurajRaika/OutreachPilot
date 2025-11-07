from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import CreateSessionRequest, SessionActionRequest, SessionResponse
from manager import session_manager
from automation_actions import AutomationActions
import os
router = APIRouter()

# Session Management Routes

@router.post("/sessions/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new automation session"""
    try:
        session_id = session_manager.create_session(
            session_type=request.session_type,
            config=request.config
        )
        
        # Store headless preference in session config
        session = session_manager.get_session(session_id)
        if session:
            headless_mode = getattr(request, 'headless', False)
            session.config['headless'] = headless_mode
        
        return SessionResponse(
            success=True,
            message="Session created successfully",
            data={"session_id": session_id, "headless": headless_mode}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/init-driver")
async def init_driver(session_id: str):
    """Initialize the browser driver (opens Chrome window)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.driver:
        return {"success": True, "message": "Driver already initialized"}
    
    headless = session.config.get('headless', False)
    success = session.create_driver(session_id,headless=headless)
    
    if success:
        return {"success": True, "message": "Driver initialized", "headless": headless}
    else:
        raise HTTPException(status_code=500, detail="Failed to initialize driver")


@router.get("/sessions/list")
async def list_sessions():
    """List all active sessions"""
    sessions = session_manager.list_sessions()
    return {"success": True, "sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "session": session.get_info()}

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session deleted"}

@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause a session"""
    success = session_manager.pause_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or cannot be paused")
    
    return {"success": True, "message": "Session paused"}

@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a paused session"""
    success = session_manager.resume_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or cannot be resumed")
    
    return {"success": True, "message": "Session resumed"}

@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a session"""
    success = session_manager.stop_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session stopped"}

# Session Messages & Live Updates

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    since: Optional[str] = Query(None, description="Get messages since this timestamp"),
    limit: int = Query(50, description="Maximum number of messages to return")
):
    """Get messages from a session (for live updates)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = session.get_messages(since=since, limit=limit)
    return {
        "success": True,
        "session_id": session_id,
        "messages": [msg.dict() for msg in messages]
    }

# Automation Action Routes

@router.post("/sessions/{session_id}/actions/navigate")
async def navigate(session_id: str, url: str):
    """Navigate to a URL"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Pass None to let navigate use session config
    result = await AutomationActions.navigate(session, url, headless=None)
    return result

@router.post("/sessions/{session_id}/actions/click")
async def click_element(session_id: str, selector: str, by: str = "css"):
    """Click an element"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.click_element(session, selector, by)
    return result

@router.post("/sessions/{session_id}/actions/type")
async def type_text(session_id: str, selector: str, text: str, by: str = "css"):
    """Type text into an element"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.type_text(session, selector, text, by)
    return result

@router.post("/sessions/{session_id}/actions/scrape")
async def scrape_element(
    session_id: str, 
    selector: str, 
    by: str = "css",
    attribute: Optional[str] = None
):
    """Scrape data from an element"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.scrape_element(session, selector, by, attribute)
    return result

@router.post("/sessions/{session_id}/actions/scrape-multiple")
async def scrape_multiple(session_id: str, selector: str, by: str = "css"):
    """Scrape multiple elements"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.scrape_multiple(session, selector, by)
    return result

@router.get("/sessions/{session_id}/actions/page-source")
async def get_page_source(session_id: str):
    """Get the full page source"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.get_page_source(session)
    return result

@router.post("/sessions/{session_id}/actions/execute-script")
async def execute_script(session_id: str, script: str):
    """Execute JavaScript code"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.execute_script(session, script)
    return result

# WhatsApp Specific Routes


@router.post("/sessions/{session_id}/whatsapp/init")
async def init_whatsapp(session_id: str):
    """Initialize WhatsApp Web"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Pass None to let navigate use session config
    result = await AutomationActions.Initialize(session, "https://web.whatsapp.com", headless=None)
    session.update_metadata("whatsapp_initialized", True)
    return result







@router.get("/sessions_list")
async def get_existing_sessions():
    base_path = "/home/suraj/chrome_selenium"
    print("DEBUG: Checking path ->", base_path)
    print("DEBUG: Exists? ->", os.path.exists(base_path))
    print("DEBUG: CWD ->", os.getcwd())

    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail="Session directory not found")

    sessions = os.listdir(base_path)
    print("DEBUG: Found sessions:", sessions)

    session_ids = []
    for session in sessions:
        if session.startswith("session_"):
            session_ids.append(session.replace("session_", "", 1))

    if not session_ids:
        raise HTTPException(status_code=404, detail=session)

    return {
        "success": True,
        "message": f"{len(session_ids)} session(s) found",
        "sessions": [{"session_id": sid} for sid in session_ids]
    }

@router.get("/sessions/{session_id}/whatsapp/qr-code")
async def get_qr_code(session_id: str):
    """Get WhatsApp QR code as base64"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get QR code element
    result = await AutomationActions.scrape_element(
        session, 
        "canvas", 
        by="css",
        attribute="src"
    )
    return result