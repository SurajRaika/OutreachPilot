import uuid
import os
from typing import Dict, Optional, List
from session import AutomationSession
from models import SessionStatus, AgentType

class SessionManager:
    """Manages multiple WhatsApp automation sessions"""
    
    SEPARATOR = "||"
    
    def __init__(self):
        self.sessions: Dict[str, AutomationSession] = {}
    
    @staticmethod
    def encode_session_id(base_uuid: str, profile_name: str) -> str:
        """Encode profile_name into session_id: uuid||profile_name"""
        return f"{base_uuid}{SessionManager.SEPARATOR}{profile_name}"
    
    @staticmethod
    def decode_session_id(encoded_id: str) -> tuple:
        """Decode session_id to get (base_uuid, profile_name)"""
        if SessionManager.SEPARATOR in encoded_id:
            parts = encoded_id.split(SessionManager.SEPARATOR, 1)
            return parts[0], parts[1]
        return encoded_id, None
    
    def create_session(self, profile_name: str, session_id: Optional[str] = None, session_type: str = "whatsapp", config: dict = None) -> str:
        """Create or resume a session with profile name"""
        if session_id and session_id in self.sessions:
            return session_id
        
        base_uuid = session_id.split(self.SEPARATOR)[0] if session_id else str(uuid.uuid4())
        encoded_id = self.encode_session_id(base_uuid, profile_name)
        
        if encoded_id in self.sessions:
            return encoded_id
        
        session = AutomationSession(encoded_id, profile_name, session_type, config)
        self.sessions[encoded_id] = session
        
        session.add_message("status", {
            "message": "Session created",
            "session_id": encoded_id,
            "profile": profile_name
        })
        
        return encoded_id
    
    def get_session(self, session_id: str) -> Optional[AutomationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        session = self.sessions.get(session_id)
        if session:
            session.cleanup()
            del self.sessions[session_id]
            return True
        return False
    
    def pause_session(self, session_id: str) -> bool:
        """Pause session (closes browser, keeps state)"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            if session.driver:
                session.cleanup()
            session.status = SessionStatus.PAUSED
            session.add_message("status", {"message": "Session paused"})
            return True
        return False
    
    def resume_session(self, session_id: str) -> bool:
        """Resume paused session"""
        session = self.sessions.get(session_id)
        if session and session.status == SessionStatus.PAUSED:
            session.status = SessionStatus.ACTIVE
            session.add_message("status", {"message": "Session resumed"})
            return True
        return False
    
    def stop_session(self, session_id: str) -> bool:
        """Stop session (closes browser, preserves profile)"""
        session = self.sessions.get(session_id)
        if session:
            if session.driver:
                session.cleanup()
            session.status = SessionStatus.STOPPED
            session.add_message("status", {"message": "Session stopped"})
            return True
        return False
    
    def list_sessions(self) -> List[dict]:
        """List all active sessions"""
        return [s.get_info() for s in self.sessions.values()]
    
    def list_saved_profiles(self) -> List[dict]:
        """List saved profiles on disk"""
        base_path = "/home/suraj/chrome_selenium"
        
        if not os.path.exists(base_path):
            return []
        
        profiles = []
        for item in os.listdir(base_path):
            path = os.path.join(base_path, item)
            if item.startswith("session_") and os.path.isdir(path):
                # Extract encoded session_id from directory name
                encoded_id = item.replace("session_", "", 1)
                base_uuid, profile_name = self.decode_session_id(encoded_id)
                
                is_active = encoded_id in self.sessions
                profiles.append({
                    "encoded_session_id": encoded_id,
                    "base_uuid": base_uuid,
                    "profile_name": profile_name or "Unknown",
                    "is_active": is_active
                })
        
        return profiles

session_manager = SessionManager()
