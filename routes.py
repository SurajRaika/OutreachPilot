
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models import CreateSessionRequest, SessionActionRequest, SessionResponse, AgentType, AgentConfig
from manager import session_manager
from automation_actions import AutomationActions
import os
from manager import session_manager, SessionManager
from models import SessionStatus, AgentType
import asyncio

router = APIRouter()


@router.post("/sessions/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new session with profile name and auto-initialize driver"""
    try:
        # Step 1: Create the session
        session_id = session_manager.create_session(
            profile_name=request.profile_name,
            session_type=request.session_type,
            config=request.config
        )

        session = session_manager.get_session(session_id)
        session.config['headless'] = request.headless

        # Step 2: Call init_driver route programmatically
        # We directly call the same function defined for /sessions/{session_id}/init-driver
        init_result = await init_driver(session_id)

        return SessionResponse(
            success=True,
            message=f"Session created with profile '{request.profile_name}' "
                    f"and driver initialized: {init_result['message']}",
            data={"session_id": session_id, "profile_name": request.profile_name}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/resume", response_model=SessionResponse)
async def resume_session(session_id: str, headless: bool = False):
    """Resume a saved session from disk and auto-initialize driver"""
    try:
        base_uuid, profile_name = SessionManager.decode_session_id(session_id)
        if not profile_name:
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        # Step 1: Resume session
        resumed_id = session_manager.create_session(
            profile_name=profile_name,
            session_id=session_id,
            session_type="whatsapp"
        )

        session = session_manager.get_session(resumed_id)
        session.config['headless'] = headless

        # Step 2: Call init_driver route programmatically
        init_result = await init_driver(resumed_id)

        return SessionResponse(
            success=True,
            message=f"Session resumed with profile '{profile_name}' "
                    f"and driver initialized: {init_result['message']}",
            data={"session_id": resumed_id, "profile_name": profile_name}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/sessions/{session_id}/init-driver")
async def init_driver(session_id: str):
    """Initialize browser driver and open WhatsApp Web in background"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.driver:
        return {"success": False, "message": "Driver already active"}
    
    headless = session.config.get('headless', False)
    if session.create_driver(headless=headless):
        session.status = SessionStatus.ACTIVE

        try:
            session.driver.get("about:blank")
        except Exception as e:
            # Don’t fail initialization if tab opening fails — just log or warn
            return {
                "success": True,
                "message": f"Driver initialized, but failed to open tab: {str(e)}",
                "profile": session.profile_name
            }

        # ✅ Kick off WhatsApp init in background, don’t wait for it
        asyncio.create_task(AutomationActions.initialize(session, "https://web.whatsapp.com"))

        return {
            "success": True,
            "message": "Driver initialized; WhatsApp initialization started in background",
            "profile": session.profile_name
        }

    raise HTTPException(status_code=500, detail="Failed to initialize driver")

@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """Pause session"""
    if session_manager.pause_session(session_id):
        return SessionResponse(success=True, message="Session paused (browser closed)")
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop session"""
    if session_manager.stop_session(session_id):
        return SessionResponse(success=True, message="Session stopped (profile saved)")
    raise HTTPException(status_code=404, detail="Session not found")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete session"""
    if session_manager.delete_session(session_id):
        return SessionResponse(success=True, message="Session deleted")
    raise HTTPException(status_code=404, detail="Session not found")

@router.get("/sessions/list")
async def list_active_sessions():
    """List active sessions with profile names and session IDs"""
    sessions = session_manager.list_sessions()
    formatted = []
    for s in sessions:
        formatted.append({
            "session_id": s["session_id"],
            "profile_name": s["profile_name"],
            "status": s["status"],
            "has_driver": s["has_driver"],
            "agents": s["agents"]
        })
    return {"success": True, "sessions": formatted, "count": len(formatted)}

@router.get("/sessions/profiles")
async def list_profiles():
    """List saved profiles on disk"""
    profiles = session_manager.list_saved_profiles()
    return {"success": True, "profiles": profiles, "count": len(profiles)}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session info"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.get_info()

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, since: Optional[str] = Query(None)):
    """Get session messages"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.get_messages(since=since)}

# # Actions
# @router.post("/sessions/{session_id}/actions/navigate")
# async def navigate(session_id: str, url: str):
#     """Navigate to URL"""
#     session = session_manager.get_session(session_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Session not found")
    
#     if not session.driver:
#         raise HTTPException(status_code=400, detail="Driver not initialized")
    
#     result = await AutomationActions.initialize(session, url, session.config.get('headless', False))
#     return SessionResponse(success=result.get("success", False), message="Navigation complete", data=result)

@router.post("/sessions/{session_id}/whatsapp/init")
async def init_whatsapp(session_id: str):
    """Initialize WhatsApp Web"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await AutomationActions.initialize(session, "https://web.whatsapp.com")
    return result

@router.get("/sessions/{session_id}/whatsapp/qr-code")
async def get_qr_code(session_id: str):
    """Get QR code"""
    session = session_manager.get_session(session_id)
    if not session or not session.driver:
        raise HTTPException(status_code=400, detail="Session/driver not ready")
    
    result = await AutomationActions.get_qr_code_if_logout(session)
    return result

# Agent Management
@router.post("/sessions/{session_id}/agents/{agent_type}/enable")
async def enable_agent(session_id: str, agent_type: str, config: Optional[dict] = None):
    """Enable agent"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        agent_enum = AgentType(agent_type)
        await session.enable_agent(agent_enum, config)
        return SessionResponse(success=True, message=f"Agent {agent_type} enabled")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}. Must be 'autoreply' or 'auto_outreach'")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sessions/{session_id}/agents/{agent_type}/disable")
async def disable_agent(session_id: str, agent_type: str):
    """Disable agent"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        agent_enum = AgentType(agent_type)
        await session.disable_agent(agent_enum)
        return SessionResponse(success=True, message=f"Agent {agent_type} disabled")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}. Must be 'autoreply' or 'auto_outreach'")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sessions/{session_id}/agents/{agent_type}/pause")
async def pause_agent(session_id: str, agent_type: str):
    """Pause agent"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        agent_enum = AgentType(agent_type)
        await session.pause_agent(agent_enum)
        return SessionResponse(success=True, message=f"Agent {agent_type} paused")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}. Must be 'autoreply' or 'auto_outreach'")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sessions/{session_id}/agents/{agent_type}/resume")
async def resume_agent(session_id: str, agent_type: str):
    """Resume agent"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        agent_enum = AgentType(agent_type)
        await session.resume_agent(agent_enum)
        return SessionResponse(success=True, message=f"Agent {agent_type} resumed")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}. Must be 'autoreply' or 'auto_outreach'")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sessions/{session_id}/agents/status")
async def get_agents_status(session_id: str):
    """Get all agent statuses"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "agents": session.get_agent_statuses()}

# Action Routes
@router.post("/sessions/{session_id}/actions/send-message")
async def send_message_route(session_id: str, contact: str, message: str):
    """Send message to contact"""
    session = session_manager.get_session(session_id)
    if not session or not session.driver:
        raise HTTPException(status_code=400, detail="Session/driver not ready")
    
    result = await AutomationActions.send_message(session, contact, message)
    return result
