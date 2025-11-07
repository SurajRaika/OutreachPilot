import asyncio
from datetime import datetime
from typing import Optional, List
from selenium import webdriver

from models import SessionStatus, SessionMessage
from driver_manager import DriverManager

class AutomationSession:
    """Represents a single automation session"""
    
    def __init__(self, session_id: str, session_type: str = "whatsapp", config: dict = None):
        self.session_id = session_id
        self.session_type = session_type
        self.config = config or {}
        self.status = SessionStatus.ACTIVE
        self.created_at = datetime.now().isoformat()
        self.driver: Optional[webdriver.Chrome] = None
        self.messages: List[SessionMessage] = []
        self.max_messages = 100
        self.task: Optional[asyncio.Task] = None
        self.metadata = {}
        
    def create_driver(self, headless: bool = False):
        """Initialize the Chrome driver for this session"""
        try:
            self.driver = DriverManager.create_driver(self.session_id, headless)
            self.add_message("log", {"message": "Driver created successfully"})
            return True
        except Exception as e:
            self.add_message("error", {"message": f"Failed to create driver: {str(e)}"})
            self.status = SessionStatus.ERROR
            return False
    
    def add_message(self, msg_type: str, content: dict):
        """Add a message to the session's message queue"""
        message = SessionMessage(
            timestamp=datetime.now().isoformat(),
            type=msg_type,
            content=content
        )
        self.messages.append(message)
        
        # Keep only the last N messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self, since: Optional[str] = None, limit: int = 50) -> List[SessionMessage]:
        """Get messages, optionally filtered by timestamp"""
        if since:
            filtered = [m for m in self.messages if m.timestamp > since]
            return filtered[-limit:]
        return self.messages[-limit:]
    
    def get_info(self) -> dict:
        """Get session information"""
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "status": self.status,
            "created_at": self.created_at,
            "message_count": len(self.messages),
            "has_driver": self.driver is not None,
            "metadata": self.metadata
        }
    
    def update_metadata(self, key: str, value: any):
        """Update session metadata"""
        self.metadata[key] = value
        self.add_message("metadata", {"key": key, "value": value})
    
    def cleanup(self):
        """Clean up session resources"""
        DriverManager.safe_quit(self.driver)
        self.driver = None
        
        if self.task and not self.task.done():
            self.task.cancel()
        
        self.status = SessionStatus.STOPPED
        self.add_message("status", {"message": "Session cleaned up"})