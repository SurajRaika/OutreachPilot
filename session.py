import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from selenium import webdriver
from models import SessionStatus, SessionMessage, AgentType, AgentStatus
from driver_manager import DriverManager

class Agent:
    """Base agent class"""
    def __init__(self, agent_type: AgentType, config: dict = None):
        self.agent_type = agent_type
        self.config = config or {}
        self.status = AgentStatus.DISABLED
        self.task: Optional[asyncio.Task] = None
        self.error: Optional[str] = None
    
    async def start(self):
        """Start the agent"""
        try:
            self.status = AgentStatus.ENABLED
            self.task = asyncio.create_task(self._run())
        except Exception as e:
            self.error = str(e)
            self.status = AgentStatus.ERROR
    
    async def stop(self):
        """Stop the agent"""
        if self.task and not self.task.done():
            self.task.cancel()
        self.status = AgentStatus.DISABLED
        self.task = None
    
    async def pause(self):
        """Pause agent execution"""
        self.status = AgentStatus.DISABLED
    
    async def resume(self):
        """Resume agent execution"""
        self.status = AgentStatus.ENABLED
    
    async def _run(self):
        """Override in subclass"""
        pass

class AutoReplyAgent(Agent):
    """Handles automatic replies to messages"""
    async def _run(self):
        while self.status == AgentStatus.ENABLED:
            try:
                # Placeholder: Add your autoreply logic here
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error = str(e)
                self.status = AgentStatus.ERROR

class AutoOutreachAgent(Agent):
    """Handles automatic outreach campaigns"""
    async def _run(self):
        while self.status == AgentStatus.ENABLED:
            try:
                # Placeholder: Add your outreach logic here
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error = str(e)
                self.status = AgentStatus.ERROR

class AutomationSession:
    """Represents a single WhatsApp automation session"""
    
    def __init__(self, session_id: str, profile_name: str, session_type: str = "whatsapp", config: dict = None):
        self.session_id = session_id
        self.profile_name = profile_name
        self.session_type = session_type
        self.config = config or {}
        self.status = SessionStatus.ACTIVE
        self.created_at = datetime.now().isoformat()
        self.driver: Optional[webdriver.Chrome] = None
        self.messages: List[SessionMessage] = []
        self.max_messages = 100
        self.metadata = {}
        
        # Agent management
        self.agents: Dict[AgentType, Agent] = {
            AgentType.AUTOREPLY: AutoReplyAgent(AgentType.AUTOREPLY),
            AgentType.AUTO_OUTREACH: AutoOutreachAgent(AgentType.AUTO_OUTREACH),
        }
    
    def create_driver(self, headless: bool = False):
        """Initialize Chrome driver"""
        try:
            self.driver = DriverManager.create_driver(self.session_id, self.profile_name, headless)
            self.add_message("log", {"message": "Driver created successfully", "profile": self.profile_name})
            return True
        except Exception as e:
            self.add_message("error", {"message": f"Failed to create driver: {str(e)}"})
            self.status = SessionStatus.ERROR
            return False
    
    def add_message(self, msg_type: str, content: dict):
        """Add message to queue"""
        message = SessionMessage(
            timestamp=datetime.now().isoformat(),
            type=msg_type,
            content=content
        )
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self, since: Optional[str] = None, limit: int = 50) -> List[SessionMessage]:
        """Get messages"""
        if since:
            filtered = [m for m in self.messages if m.timestamp > since]
            return filtered[-limit:]
        return self.messages[-limit:]
    
    async def enable_agent(self, agent_type: AgentType, config: dict = None):
        """Enable an agent"""
        if agent_type not in self.agents:
            return False
        
        agent = self.agents[agent_type]
        if config:
            agent.config = config
        
        await agent.start()
        self.add_message("log", {"message": f"Agent {agent_type.value} enabled"})
        return True
    
    async def disable_agent(self, agent_type: AgentType):
        """Disable an agent"""
        if agent_type not in self.agents:
            return False
        
        agent = self.agents[agent_type]
        await agent.stop()
        self.add_message("log", {"message": f"Agent {agent_type.value} disabled"})
        return True
    
    async def pause_agent(self, agent_type: AgentType):
        """Pause an agent"""
        if agent_type not in self.agents:
            return False
        
        agent = self.agents[agent_type]
        await agent.pause()
        self.add_message("log", {"message": f"Agent {agent_type.value} paused"})
        return True
    
    async def resume_agent(self, agent_type: AgentType):
        """Resume an agent"""
        if agent_type not in self.agents:
            return False
        
        agent = self.agents[agent_type]
        await agent.resume()
        self.add_message("log", {"message": f"Agent {agent_type.value} resumed"})
        return True
    
    def get_agent_statuses(self) -> Dict[str, str]:
        """Get all agent statuses"""
        return {agent_type.value: agent.status.value for agent_type, agent in self.agents.items()}
    
    def get_info(self) -> dict:
        """Get session info"""
        return {
            "session_id": self.session_id,
            "profile_name": self.profile_name,
            "session_type": self.session_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "message_count": len(self.messages),
            "has_driver": self.driver is not None,
            "metadata": self.metadata,
            "agents": self.get_agent_statuses()
        }
    
    def update_metadata(self, key: str, value):
        """Update metadata"""
        self.metadata[key] = value
        self.add_message("metadata", {"key": key, "value": value})
    
    def cleanup(self):
        """Clean up resources"""
        DriverManager.safe_quit(self.driver)
        self.driver = None
        self.status = SessionStatus.STOPPED
        self.add_message("status", {"message": "Session cleaned up"})
