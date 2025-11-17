import asyncio
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING
from selenium import webdriver
from models import SessionStatus, SessionMessage, AgentType, AgentStatus
from driver_manager import DriverManager

if TYPE_CHECKING:
    from agents import BaseAgent









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
        self.max_messages = 20
        self.metadata = {}
        
        # Agent management - initialize as empty dict
        # Agents will be created lazily when first enabled
        self.agents: Dict[AgentType, "BaseAgent"] = {}
    
    def _get_or_create_agent(self, agent_type: AgentType) -> "BaseAgent":
        """Get existing agent or create new one"""
        if agent_type not in self.agents:
            # Import here to avoid circular dependency
            from agents import AutoReplyAgent, AutoOutreachAgent
            
            if agent_type == AgentType.AUTOREPLY:
                self.agents[agent_type] = AutoReplyAgent(self,{
    "reply_delay": 2,
    "check_interval": 5,
    "gemini_api_key": "AIzaSyBmX1jEygYWngFlDX22Fb0_Vovy0HLRQzU",
    "system_instruction": "You are a helpful customer service bot. Keep responses friendly and concise.",
    "model": "gemini-1.5-flash",
})
            elif agent_type == AgentType.AUTO_OUTREACH:
                self.agents[agent_type] = AutoOutreachAgent(self)
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
        
        return self.agents[agent_type]
    
    def create_driver(self, headless: bool = True):
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

        # Keep message count within limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        # ANSI colors for types and parts
        COLORS = {
            "status": "\033[94m",   # Blue
            "log": "\033[92m",      # Green
            "action": "\033[93m",   # Yellow
            "default": "\033[91m",  # Red
            "timestamp": "\033[90m",# Gray
            "key": "\033[95m",      # Magenta
            "value": "\033[97m",    # White
        }
        RESET = "\033[0m"

        # Format timestamp nicely
        time_str = datetime.fromisoformat(message.timestamp).strftime("%H:%M:%S")

        # Choose color for message type
        color = COLORS.get(msg_type.lower(), COLORS["default"])

        # Pretty format message content (key-value lines)
        pretty_content = "\n".join(
            f"  {COLORS['key']}{k}{RESET}: {COLORS['value']}{v}{RESET}"
            for k, v in content.items()
        )

        # Print formatted block
        print(
            f"\n{COLORS['timestamp']}[{time_str}]{RESET} "
            f"{color}{msg_type.upper()}{RESET}\n"
            f"{pretty_content}\n"
            f"{COLORS['timestamp']}{'-' * 40}{RESET}"
        )

    def get_messages(self, since: Optional[str] = None, limit: int = 50) -> List[SessionMessage]:
        """Get messages"""
        if since:
            filtered = [m for m in self.messages if m.timestamp > since]
            return filtered[-limit:]
        return self.messages[-limit:]
    
    # Updated enable_agent method in the session manager (if needed)
    async def enable_agent(self, agent_type: AgentType, list_of_contact: List[str] = [], messageTemplate: str = "", ai_instruction: str = ""):

        
        """Enable an agent with optional configuration"""
        try:
            # Create or retrieve the agent
            agent = self._get_or_create_agent(agent_type)

            # Update agent's attributes if values are provided
            if list_of_contact:
                agent.list_of_contact = list_of_contact
            if messageTemplate:
                agent.messageTemplate = messageTemplate
            if ai_instruction:
                agent.ai_instruction = ai_instruction

            # Start the agent
            await agent.start()
            
            # Log the success
            self.add_message("log", {"message": f"Agent {agent_type.value} enabled"})
            return True
        except Exception as e:
            # Log the error if any exception occurs
            self.add_message("error", {"message": f"Failed to enable agent {agent_type.value}: {str(e)}"})
            return False

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
        statuses = {}
        for agent_type in AgentType:
            if agent_type == AgentType.NONE:
                continue
            if agent_type in self.agents:
                statuses[agent_type.value] = self.agents[agent_type].status.value
            else:
                statuses[agent_type.value] = AgentStatus.DISABLED.value
        return statuses
    
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
    
    async def cleanup_agents(self):
        """Stop all agents before cleanup"""
        for agent in self.agents.values():
            await agent.stop()
    
    def cleanup(self):
        """Clean up resources"""
        # Stop all agents first
        if self.agents:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup_agents())
                else:
                    loop.run_until_complete(self.cleanup_agents())
            except Exception as e:
                print(f"Error stopping agents during cleanup: {e}")
        
        DriverManager.safe_quit(self.driver)
        self.driver = None
        self.status = SessionStatus.STOPPED
        self.add_message("status", {"message": "Session cleaned up"})