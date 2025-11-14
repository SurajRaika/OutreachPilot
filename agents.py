import asyncio
from enum import Enum
from typing import Optional, Dict, TYPE_CHECKING
import google.generativeai as genai

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
    Handles automatic replies to incoming messages using Gemini API
    
    Config example:
    {
        "reply_delay": 2,
        "check_interval": 5,
        "target_contacts": ["contact1", "contact2"],
        "gemini_api_key": "your-api-key",
        "system_instruction": "You are a helpful WhatsApp bot. Keep responses concise and friendly.",
        "model": "gemini-1.5-flash"
    }
    """
    
    def __init__(self, session: "AutomationSession", config: dict = None):
        super().__init__(AgentType.AUTOREPLY, config)
        self.session = session
        self.model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini API with configuration"""
        api_key = self.config.get("gemini_api_key")
        model_name = self.config.get("model", "gemini-1.5-flash")
        
        if not api_key:
            raise ValueError("gemini_api_key is required in config")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    async def _generate_reply(self, incoming_message: str) -> str:
        """
        Generate a reply using Gemini API based on incoming message and system instruction
        """
        try:
            system_instruction = self.config.get(
                "system_instruction", 
                "You are a helpful WhatsApp assistant. Keep responses concise and friendly."
            )
            
            # Create the prompt with system instruction context
            prompt = f"""System Instruction: {system_instruction}

                Incoming Message: {incoming_message}

                Generate an appropriate reply based on the system instruction. Keep the response concise for WhatsApp (under 1000 characters)."""
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            reply_text = response.text.strip()
            
            return reply_text
        
        except Exception as e:
            self.session.add_message("error", {
                "agent": "autoreply",
                "action": "generate_reply",
                "error": str(e)
            })
            # Fallback reply if Gemini fails
            return "Thanks for your message! I'll get back to you soon."
    
    async def _run(self):
        self.session.add_message("status", {"message": "AutoReplyAgent Intisted but not running"})
        """Main loop: checks unread chats and replies using Gemini API."""
        try:
            reply_delay = self.config.get("reply_delay", 2)
            check_interval = self.config.get("check_interval", 5)

            self.session.add_message("log", {
                "agent": "autoreply",
                "event": "started",
                "config": {
                    "model": self.config.get("model", "gemini-1.5-flash"),
                    "reply_delay": reply_delay,
                    "check_interval": check_interval,
                    "system_instruction": self.config.get("system_instruction", "")
                }
            })

            from automation_actions import AutomationActions

            while True:
                # 🟡 Check if paused or disabled before every iteration
                if self.status != AgentStatus.ENABLED:
                    await asyncio.sleep(0.5)
                    continue

                try:
                    # 🔍 Step 1: Find unread chats
                    result = await AutomationActions.open_unread_chats(self.session)

                    # Check pause state before processing results
                    if self.status != AgentStatus.ENABLED:
                        continue

                    if not result.get("success"):
                        # ❌ Driver or list error
                        self.session.add_message("error", {
                            "agent": "autoreply",
                            "action": "open_unread_chats",
                            "error": result.get("error")
                        })
                        await asyncio.sleep(check_interval)
                        continue

                    # ✅ Case 1: No unread chats
                    if result.get("message") == "No unread chats found" or result.get("total_unread", 0) == 0:
                        self.session.add_message("log", {
                            "agent": "autoreply",
                            "event": "no_unread_chats"
                        })

                        await asyncio.sleep(check_interval)
                        continue

                    # ✅ Case 2: There are unread chats
                    opened_chats = result.get("opened_chats", [])
                    self.session.add_message("log", {
                        "agent": "autoreply",
                        "event": "found_unread_chats",
                        "count": len(opened_chats)
                    })
                    self.session.add_message("status", {"message": "unread chat Found and Opening "})


                    for chat_info in opened_chats:
                        if self.status != AgentStatus.ENABLED:
                            break

                        try:
                            contact = chat_info.get("contact") or chat_info.get("name") or "Unknown"
                            number = chat_info.get("number")
                            incoming_message = chat_info.get("message", "")
                            


                            # Wait a bit before replying (respect delay)
                            for _ in range(int(reply_delay * 10)):  # check every 0.1s
                                if self.status != AgentStatus.ENABLED:
                                    break
                                await asyncio.sleep(0.1)
                            if self.status != AgentStatus.ENABLED:
                                break
                            self.session.add_message("status", {"message": "Generating Reply ......."})

                            # 🤖 Step 2: Generate reply using Gemini API
                            reply_message = await self._generate_reply(incoming_message)

                            # 💬 Step 3: Send and close chat
                            self.session.add_message("status", {"message": "Writing the msg .......&{{reply_message}}"})

                            send_result = await AutomationActions.SendAndCloseChat(
                                self.session,  reply_message
                            )

                            self.session.add_message("log", {
                                "agent": "autoreply",
                                "action": "reply_sent",
                                "contact": contact,
                                "number": number,
                                "incoming_message": incoming_message,
                                "generated_reply": reply_message,
                                "result": send_result
                            })

                        except Exception as e:
                            self.session.add_message("error", {
                                "agent": "autoreply",
                                "action": "reply_chat",
                                "error": str(e)
                            })
                            continue

                    # 🕒 Wait between cycles with pause-awareness
                    for _ in range(int(check_interval * 10)):  # check every 0.1s
                        if self.status != AgentStatus.ENABLED:
                            break
                        await asyncio.sleep(0.1)

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