from pydantic import BaseModel
from enum import Enum
from typing import Optional

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class SessionMessage(BaseModel):
    timestamp: str
    type: str  # 'log', 'data', 'error', 'status'
    content: dict

class CreateSessionRequest(BaseModel):
    """
    Request model for creating a new session or resuming an existing one.
    If session_id is provided, the manager will attempt to use it.
    """
    # ADDED: Optional session_id for resuming saved sessions from disk profile
    session_id: Optional[str] = None 
    session_type: str = "whatsapp"
    config: Optional[dict] = None
    headless: Optional[bool] = False  # Default to GUI mode for testing

class SessionActionRequest(BaseModel):
    action: str  # 'navigate', 'click', 'scrape', 'type', etc.
    params: dict

class SessionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class Msg(BaseModel):
    msg: str
    secret: str