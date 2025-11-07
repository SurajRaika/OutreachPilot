import uuid
from typing import Dict, Optional, List

from session import AutomationSession
from models import SessionStatus

class SessionManager:
    """Manages multiple automation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, AutomationSession] = {}
    
    def create_session(self, session_type: str = "whatsapp", config: dict = None, session_id: Optional[str] = None) -> str:
        """
        Create a new automation session or load an existing one.
        If session_id is provided, it is used instead of generating a new UUID.
        """
        if session_id:
            # 1. Check if session is already active in memory
            if session_id in self.sessions:
                self.sessions[session_id].add_message("log", {"message": f"Session {session_id} is already active in memory."})
                return session_id
            
            # 2. Resume/Load path: use the provided ID
            new_session_id = session_id
            message_prefix = "Session resumed"
        else:
            # 3. New session path: generate a new UUID
            new_session_id = str(uuid.uuid4())
            message_prefix = "Session created"
        
        # Create a new AutomationSession instance (this loads metadata but does not start the driver)
        session = AutomationSession(new_session_id, session_type, config)
        self.sessions[new_session_id] = session
        
        session.add_message("status", {
            "message": f"{message_prefix} successfully",
            "session_id": new_session_id
        })
        
        return new_session_id
    
    def get_session(self, session_id: str) -> Optional[AutomationSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and clean up resources"""
        session = self.sessions.get(session_id)
        if session:
            # Note: The underlying user-data-dir is *not* deleted by cleanup, 
            # ensuring persistence for resume unless explicitly handled later.
            session.cleanup() 
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[dict]:
        """List all sessions with their info"""
        return [session.get_info() for session in self.sessions.values()]
    
    def pause_session(self, session_id: str) -> bool:
        """Pause a session (closes browser, status PAUSED)"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            # Clean up the driver but keep the session object in memory for fast restart
            if session.driver:
                session.cleanup() 

            session.status = SessionStatus.PAUSED
            session.add_message("status", {"message": "Session paused (driver closed)"})
            return True
        return False
    
    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session (just changes status in memory)"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.ACTIVE
            session.add_message("status", {"message": "Session status set to active. Run /init-driver to restart browser."})
            return True
        return False
    
    def stop_session(self, session_id: str) -> bool:
        """Stop a session without deleting it (closes browser, status STOPPED)"""
        session = self.sessions.get(session_id)
        if session:
            # Clean up the driver but keep the session object in memory for fast restart
            if session.driver:
                session.cleanup() 

            session.status = SessionStatus.STOPPED
            session.add_message("status", {"message": "Session stopped (driver closed). Profile preserved on disk."})
            return True
        return False

# Global session manager instance
session_manager = SessionManager()