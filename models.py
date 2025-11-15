from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class AgentType(str, Enum):
    AUTOREPLY = "autoreply"
    AUTO_OUTREACH = "auto_outreach"
    NONE = "none"

class AgentStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"

class SessionMessage(BaseModel):
    timestamp: str
    type: str
    content: dict
    
class EnableAgentRequest(BaseModel):
    list_of_contact: Optional[List[str]] = []
    messageTemplate: Optional[str] = ""
    ai_instruction: Optional[str] = ""

class CreateSessionRequest(BaseModel):
    profile_name: Optional[str] = None  # Optional for resuming from disk
    session_id: Optional[str] = None
    session_type: str = "whatsapp"
    config: Optional[dict] = None
    headless: Optional[bool] = False

class SessionActionRequest(BaseModel):
    action: str
    params: dict

class AgentConfig(BaseModel):
    agent_type: AgentType
    enabled: bool = False
    config: Dict = {}

class SessionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class SessionInfoResponse(BaseModel):
    session_id: str
    profile_name: str
    session_type: str
    status: SessionStatus
    created_at: str
    message_count: int
    has_driver: bool
    metadata: dict
    agents: Dict[str, AgentStatus]
