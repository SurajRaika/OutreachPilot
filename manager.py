import uuid
from typing import Dict, Optional, List

from session import AutomationSession
from models import SessionStatus

class SessionManager:
    """Manages multiple automation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, AutomationSession] = {}
    
    def create_session(self, session_type: str = "whatsapp", config: dict = None) -> str:
        """Create a new automation session"""
        session_id = str(uuid.uuid4())
        session = AutomationSession(session_id, session_type, config)
        self.sessions[session_id] = session
        
        session.add_message("status", {
            "message": "Session created",
            "session_id": session_id
        })
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AutomationSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up resources"""
        session = self.sessions.get(session_id)
        if session:
            session.cleanup()
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[dict]:
        """List all sessions with their info"""
        return [session.get_info() for session in self.sessions.values()]
    
    def pause_session(self, session_id: str) -> bool:
        """Pause a session"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.PAUSED
            session.add_message("status", {"message": "Session paused"})
            return True
        return False
    
    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.ACTIVE
            session.add_message("status", {"message": "Session resumed"})
            return True
        return False
    
    def stop_session(self, session_id: str) -> bool:
        """Stop a session without deleting it"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.STOPPED
            session.add_message("status", {"message": "Session stopped"})
            if session.driver:
                session.cleanup()
            return True
        return False

# Global session manager instance
session_manager = SessionManager()