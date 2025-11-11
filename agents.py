"""
agents.py - WhatsApp automation agents
"""
import asyncio
from enum import Enum
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from session import AutomationSession

class AgentType(str, Enum):
    AUTOREPLY = "autoreply"
    AUTO_OUTREACH = "auto_outreach"
    NONE = "none"

class AgentStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"

class BaseAgent:
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

class AutoReplyAgent(BaseAgent):
    """
    Handles automatic replies to incoming messages
    
    Config example:
    {
        "reply_delay": 2,
        "reply_message": "Thanks for your message!",
        "check_interval": 5,
        "target_contacts": ["contact1", "contact2"]
    }
    """
    
    def __init__(self, session: "AutomationSession", config: dict = None):
        super().__init__(AgentType.AUTOREPLY, config)
        self.session = session
    
    async def _run(self):
        """Run autoreply agent"""
        try:
            reply_delay = self.config.get("reply_delay", 2)
            reply_message = self.config.get("reply_message", "Thanks for reaching out!")
            check_interval = self.config.get("check_interval", 5)
            target_contacts = self.config.get("target_contacts", [])
            
            self.session.add_message("log", {
                "agent": "autoreply",
                "event": "started",
                "config": {
                    "reply_message": reply_message,
                    "reply_delay": reply_delay,
                    "target_contacts": target_contacts
                }
            })
            
            while self.status == AgentStatus.ENABLED:
                try:
                    # TODO: Add your message detection logic here
                    await asyncio.sleep(check_interval)
                    self.session.add_message("log", {
                            "agent": "autoreply",
                            "event": "running1......"
                           
                        })

                                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.error = str(e)
                    self.status = AgentStatus.ERROR
                    self.session.add_message("error", {
                        "agent": "autoreply",
                        "error": str(e)
                    })
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            pass
        finally:
            self.session.add_message("log", {
                "agent": "autoreply",
                "event": "stopped"
            })
    
    async def send_autoreply(self, contact: str, message: str):
        """Send autoreply to contact"""
        try:
            # Import here to avoid circular dependency
            from automation_actions import AutomationActions
            
            delay = self.config.get("reply_delay", 2)
            await asyncio.sleep(delay)
            
            result = await AutomationActions.send_message(self.session, contact, message)
            
            self.session.add_message("log", {
                "agent": "autoreply",
                "action": "message_sent",
                "contact": contact,
                "success": result.get("success")
            })
            
            return result
        except Exception as e:
            self.session.add_message("error", {
                "agent": "autoreply",
                "action": "send_autoreply",
                "error": str(e)
            })
            raise

class AutoOutreachAgent(BaseAgent):
    """
    Handles automatic outreach campaigns
    
    Config example:
    {
        "contacts_list": ["contact1", "contact2"],
        "outreach_message": "Hi! Check out our product...",
        "delay_between_messages": 10,
        "daily_limit": 50,
        "daily_reset_hour": 0
    }
    """
    
    def __init__(self, session: "AutomationSession", config: dict = None):
        super().__init__(AgentType.AUTO_OUTREACH, config)
        self.session = session
        self.messages_sent_today = 0
    
    async def _run(self):
        """Run auto-outreach agent"""
        try:
            # Import here to avoid circular dependency
            from automation_actions import AutomationActions
            
            contacts_list = self.config.get("contacts_list", [])
            outreach_message = self.config.get("outreach_message", "Hello!")
            delay_between = self.config.get("delay_between_messages", 10)
            daily_limit = self.config.get("daily_limit", 50)
            
            if not contacts_list:
                self.session.add_message("log", {
                    "agent": "auto_outreach",
                    "event": "no_contacts",
                    "message": "No contacts in list"
                })
                return
            
            self.session.add_message("log", {
                "agent": "auto_outreach",
                "event": "started",
                "total_contacts": len(contacts_list),
                "daily_limit": daily_limit
            })
            
            for contact in contacts_list:
                if self.status != AgentStatus.ENABLED:
                    break
                
                try:
                    if self.messages_sent_today >= daily_limit:
                        self.session.add_message("log", {
                            "agent": "auto_outreach",
                            "event": "daily_limit_reached",
                            "count": self.messages_sent_today
                        })
                        break
                    
                    result = await AutomationActions.send_message(
                        self.session, 
                        contact, 
                        outreach_message
                    )
                    
                    self.session.add_message("log", {
                        "agent": "auto_outreach",
                        "action": "message_sent",
                        "contact": contact,
                        "success": result.get("success")
                    })
                    
                    if result.get("success"):
                        self.messages_sent_today += 1
                    
                    await asyncio.sleep(delay_between)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.session.add_message("error", {
                        "agent": "auto_outreach",
                        "contact": contact,
                        "error": str(e)
                    })
                    continue
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.error = str(e)
            self.status = AgentStatus.ERROR
            self.session.add_message("error", {
                "agent": "auto_outreach",
                "error": str(e)
            })
        finally:
            self.session.add_message("log", {
                "agent": "auto_outreach",
                "event": "stopped",
                "messages_sent": self.messages_sent_today
            })
    
    async def add_contacts(self, contacts: list):
        """Add more contacts to outreach list"""
        try:
            current = self.config.get("contacts_list", [])
            self.config["contacts_list"] = current + contacts
            
            self.session.add_message("log", {
                "agent": "auto_outreach",
                "action": "contacts_added",
                "count": len(contacts),
                "total": len(self.config["contacts_list"])
            })
        except Exception as e:
            self.session.add_message("error", {
                "agent": "auto_outreach",
                "action": "add_contacts",
                "error": str(e)
            })
    
    def get_stats(self) -> dict:
        """Get outreach statistics"""
        return {
            "messages_sent_today": self.messages_sent_today,
            "daily_limit": self.config.get("daily_limit", 50),
            "total_contacts": len(self.config.get("contacts_list", [])),
            "status": self.status.value
        }