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
    """
    Create a new automation session or resume an existing one by providing a session_id.
    """
    try:
        session_id = session_manager.create_session(
            session_id=request.session_id, # Pass optional session_id for resume
            session_type=request.session_type,
            config=request.config
        )
        
        # Store headless preference in session config
        session = session_manager.get_session(session_id)
        if session:
            headless_mode = getattr(request, 'headless', False)
            session.config['headless'] = headless_mode
            
            message = "Session created successfully"
            if request.session_id:
                message = f"Session {session_id} resumed/loaded successfully"
        
        return SessionResponse(
            success=True,
            message=message,
            data={"session_id": session_id, "headless": headless_mode}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/init-driver")
async def init_driver(session_id: str):
    """Initialize the browser driver (opens Chrome window)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found in active memory. Please ensure you /sessions/create first if resuming from disk.")
    
    if session.driver:
        return {"success": False, "message": "Driver already active"}

    # Use the headless config stored during creation/resumption
    headless_mode = session.config.get('headless', False) 
    
    if session.create_driver(headless=headless_mode):
        session.status = session.status.ACTIVE # Set status to ACTIVE after driver init
        return {"success": True, "message": "Driver initialized", "headless": headless_mode}
    else:
        # Error message is already logged in session.add_message inside create_driver
        raise HTTPException(status_code=500, detail=f"Failed to initialize driver for session {session_id}")


@router.post("/sessions/{session_id}/stop")
async def stop_session_route(session_id: str):
    """Stop the browser driver but keep the session object in memory and profile on disk."""
    if session_manager.stop_session(session_id):
        return SessionResponse(success=True, message=f"Session {session_id} stopped (browser closed). Profile remains on disk.")
    raise HTTPException(status_code=404, detail="Session not found")

@router.delete("/sessions/{session_id}")
async def delete_session_route(session_id: str):
    """Delete a session (removes from memory and closes driver)"""
    if session_manager.delete_session(session_id):
        return SessionResponse(success=True, message=f"Session {session_id} deleted.")
    raise HTTPException(status_code=404, detail="Session not found")

@router.get("/sessions/list")
async def list_active_sessions():
    """List all currently active sessions in memory"""
    sessions = session_manager.list_sessions()
    return {"success": True, "sessions": sessions, "count": len(sessions)}

@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get detailed information about a single session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.get_info()

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, since: Optional[str] = Query(None)):
    """Get the message history for a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.get_messages(since=since)}

@router.post("/sessions/{session_id}/actions/{action}")
async def handle_action(session_id: str, action: str, request: SessionActionRequest):
    """Handle a generic automation action (e.g., click, type, scrape)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.driver:
        raise HTTPException(status_code=400, detail="Driver not initialized. Please call /init-driver first.")
    
    # In a real application, you would map 'action' to methods in AutomationActions
    # For now, we only support Initialize for navigation, which must run first.
    if action.lower() == 'navigate':
        url = request.params.get('url')
        if not url:
            raise HTTPException(status_code=400, detail="URL parameter is required for 'navigate' action.")

        # Re-using Initialize for simple navigation after the session is running
        result = await AutomationActions.Initialize(session, url=url, headless=session.config.get('headless', False))
        
        return SessionResponse(
            success=result.get("success", False),
            message=f"Navigation to {url} complete.",
            data=result
        )

    # Placeholder for other actions
    session.add_message("log", {"message": f"Action '{action}' received with params: {request.params}"})
    return {"success": True, "message": f"Action '{action}' is a placeholder."}

@router.post("/sessions/{session_id}/whatsapp/initialize")
async def initialize_whatsapp(session_id: str):
    """Navigate to WhatsApp Web and attempt to get the QR code (if logged out)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Use the headless config stored during creation/resumption
    headless_mode = session.config.get('headless', False) 

    # Initializes the driver if needed and navigates.
    result = await AutomationActions.Initialize(session, "https://web.whatsapp.com", headless=headless_mode)
    session.update_metadata("whatsapp_initialized", True)
    return result


@router.get("/sessions_list")
async def get_existing_sessions():
    """List sessions saved on disk (by checking the user-data-dir folders)"""
    # NOTE: This path is hardcoded based on the existing driver_manager.py
    base_path = "/home/suraj/chrome_selenium" 
    print("DEBUG: Checking path ->", base_path)
    print("DEBUG: Exists? ->", os.path.exists(base_path))
    print("DEBUG: CWD ->", os.getcwd())

    if not os.path.exists(base_path):
        # Allow it to return an empty list instead of 404 if the folder just doesn't exist yet
        return {
            "success": True,
            "message": "No session directory found on disk.",
            "sessions": [],
            "count": 0
        }

    sessions = os.listdir(base_path)
    print("DEBUG: Found session candidates:", sessions)

    session_ids = []
    for session_dir in sessions:
        # Check for directory and correct prefix
        if session_dir.startswith("session_") and os.path.isdir(os.path.join(base_path, session_dir)):
            session_id = session_dir.replace("session_", "", 1)
            session_ids.append({
                "session_id": session_id, 
                "is_active": session_manager.get_session(session_id) is not None
            })

    return {
        "success": True,
        "message": f"{len(session_ids)} session(s) found on disk",
        "sessions": session_ids,
        "count": len(session_ids)
    }

@router.get("/sessions/{session_id}/whatsapp/qr-code")
async def get_qr_code(session_id: str):
    """Get WhatsApp QR code as base64"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.driver:
        raise HTTPException(status_code=400, detail="Driver not initialized. Please call /init-driver or /whatsapp/initialize first.")

    try:
        # This action assumes the driver is at the correct page and the QR code is visible
        result = await AutomationActions.ExtractQRCode(session)
        
        if result.get("success"):
             return {
                "success": True,
                "message": "QR Code extracted successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to extract QR code"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))