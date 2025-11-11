import uuid
import os
from typing import Dict, Optional, List , Tuple
from session import AutomationSession
from models import SessionStatus, AgentType

import base64
import re


class SessionManager:
    """Manages multiple WhatsApp automation sessions with file-safe session IDs."""

    SEPARATOR = "||"

    def __init__(self):
        self.sessions: Dict[str, "AutomationSession"] = {}

    @staticmethod
    def _sanitize_for_filename(value: str) -> str:
        """
        Make a string safe for use as a filename.
        Keeps alphanumerics, underscores, and hyphens.
        Replaces all other characters with underscores.
        """
        return re.sub(r'[^A-Za-z0-9_.-]', '_', value)

    @staticmethod
    def _encode_component(value: str) -> str:
        """
        Encode a string in a URL-safe base64 form (no padding).
        Ensures special characters are safe for filenames.
        """
        encoded = base64.urlsafe_b64encode(value.encode()).decode()
        return encoded.rstrip("=")  # remove padding to shorten filename

    @staticmethod
    def _decode_component(value: str) -> str:
        """Decode a URL-safe base64 string (adding back missing padding)."""
        padding = '=' * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding).decode()

    @classmethod
    def encode_session_id(cls, base_uuid: str, profile_name: str) -> str:
        """
        Encode profile_name into session_id: uuid||encoded_name
        Returns a string safe for filesystem use.
        """
        safe_uuid = cls._sanitize_for_filename(base_uuid)
        safe_profile = cls._encode_component(profile_name)
        return f"{safe_uuid}{cls.SEPARATOR}{safe_profile}"

    @classmethod
    def decode_session_id(cls, encoded_id: str) -> Tuple[str, Optional[str]]:
        """
        Decode session_id to get (base_uuid, profile_name)
        Returns (uuid, profile_name or None)
        """
        if cls.SEPARATOR not in encoded_id:
            return encoded_id, None

        base_uuid, encoded_profile = encoded_id.split(cls.SEPARATOR, 1)
        try:
            profile_name = cls._decode_component(encoded_profile)
        except Exception:
            # fallback if decoding fails (e.g., corrupted filename)
            profile_name = None
        return base_uuid, profile_name

    
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
            del self.sessions[session_id]
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
