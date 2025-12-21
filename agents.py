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
        # numbers are sperated by , , eahc num can be string or num i don't know
        self.list_of_contact=[]
        # intead of sending the ai genearted msg , we send this message template
        self.messageTemplate=""
        self.ai_instruction=""
    
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


def get_chat_reply(
    chathistory_text: str,
    system_instruction: str,
    gemini_api_key: str
) -> str:
    """
    Generate a reply using Google's Gemini API based on chat history and system instructions.
    
    Args:
        chathistory_text (str): The conversation history to provide context
        system_instruction (str): System instructions/prompt to guide the model's behavior
        gemini_api_key (str): Your Google Gemini API key
    
    Returns:
        str: The generated reply text
    
    Raises:
        ValueError: If any required parameter is empty
        Exception: If API call fails
    """
    
    # Validate inputs
    if not chathistory_text or not isinstance(chathistory_text, str):
        raise ValueError("chathistory_text must be a non-empty string")
    if not system_instruction or not isinstance(system_instruction, str):
        raise ValueError("system_instruction must be a non-empty string")
    if not gemini_api_key or not isinstance(gemini_api_key, str):
        raise ValueError("gemini_api_key must be a non-empty string")
    
    # Configure the API
    genai.configure(api_key=gemini_api_key)
    
    # Create the model
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_instruction
    )
    
    # Generate reply
    response = model.generate_content(chathistory_text)
    
    return response.text









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

    async def _generate_reply(self, chat_history: str) -> str:

        self.session.add_message("log", {"message": "Starting _generate_reply method"})

        API_KEY = self.config.get("gemini_api_key")
        self.session.add_message("log", {"message": f"API Key loaded: {bool(API_KEY)}"})

        if not API_KEY:
            self.session.add_message("error", {
                "agent": "autoreply",
                "action": "initialize_gemini",
                "error": "gemini_api_key is required in config"
            })
            # raise ValueError("gemini_api_key is required in config")
            return "Thanks for your message! I'll get back to you soon as right now i am dumb."


        # System instruction
        system_inst = self.config.get("system_instruction")
        # self.session.add_message("log", {"message": f"System instruction retrieved: {bool(system_inst)}"})

        try:
            self.session.add_message("log", {"message": "Calling get_chat_reply()..."})
            reply = get_chat_reply(chat_history, system_inst, API_KEY)
            self.session.add_message("log", {"message": "Reply successfully generated"})
            print("Generated Reply:", reply)
            return reply

        except Exception as e:
            self.session.add_message("error", {
                "message": "Exception occurred while generating reply",
                "exception": str(e)
            })
            self.session.add_message("log", {"message": "Fallback message returned"})
            return "Thanks for your message! I'll get back to you soon."



    async def _run(self):
            self.session.add_message("status", {"message": "AutoReplyAgent Initiated but not running"})
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
                total_chat_msg = None
                current_chat_id = None
                
                while True:
                    # 🟡 Check if paused or disabled before every iteration
                    if self.status != AgentStatus.ENABLED:
                        await asyncio.sleep(0.5)
                        continue

                    try:
                        # 🔄 Step 0: Check if current open chat has new messages
                        if current_chat_id and total_chat_msg:
                            history_res = await AutomationActions.extract_and_format_chat_history(self.session)
                            self.session.add_message("log", {"total_chat_msg": total_chat_msg,"ccurrent":history_res.get("sender_messages")})
                            
                            if history_res.get("success") and history_res.get("sender_messages") > total_chat_msg:
                                self.session.add_message("action", {
                                                    "action_type": "CHAT_OPENED",
                                                    "chat_id": current_chat_id
                                                })
                                # 🆕 New messages found in current chat - handle them first
                                self.session.add_message("status", {"message": "New message in current chat detected"})
                                
                                # Update total message count
                                total_chat_msg = history_res.get("sender_messages")
                                incoming_message = history_res.get("formatted_text", "")
                                
                                # Wait before replying
                                for _ in range(int(reply_delay * 10)):
                                    if self.status != AgentStatus.ENABLED:
                                        break
                                    await asyncio.sleep(0.1)
                                
                                if self.status != AgentStatus.ENABLED:
                                    continue
                                
                                # Generate and send reply
                                self.session.add_message("status", {"message": "Generating Reply for current chat......."})
                                reply_message = await self._generate_reply(incoming_message)
                                
                                self.session.add_message("status", {"message": f"Writing the msg .......&{reply_message}"})
                                send_result = await AutomationActions.SendAndCloseChat(self.session, reply_message)
                                # when i add this , it update the chat ui in cleint 
                                self.session.add_message("action", {
                                    "action_type": "CHAT_OPENED",
                                    "chat_id": current_chat_id
                                })
                                # After sending, continue to check for more messages
                                continue
                        
                        # 🔍 Step 1: Find unread chats (this will open other chats with unread messages)
                        result = await AutomationActions.open_unread_chat(self.session)

                        # Check pause state before processing results
                        if self.status != AgentStatus.ENABLED:
                            continue

                        if not result.get("success"):
                            # ❌ Driver or list error
                            await asyncio.sleep(check_interval)
                            continue

                        # ✅ Case 1: No unread chats
                        if not result.get("opened_chat"):
                            self.session.add_message("log", {
                                "agent": "autoreply",
                                "event": "no_unread_chats"
                            })
                            
                            # Reset current chat tracking
                            current_chat_id = None
                            total_chat_msg = None
                            
                            await asyncio.sleep(check_interval)
                            continue

                        # ✅ Case 2: There are unread chats
                        opened_chat = result.get("opened_chat")
                        chat_info = opened_chat
                        
                        if chat_info:   
                            if self.status != AgentStatus.ENABLED:
                                break

                            try:
                                # Process the newly opened chat
                                number = chat_info.get("id")
                                current_chat_id = number  # Track the current chat
                                
                                self.session.add_message("status", {"message": "unread chat Found and Opening"})
                                self.session.add_message("action", {"action_type": "highlight_chat", "chat_id": number})
                                self.session.add_message("action", {
                                    "action_type": "CHAT_OPENED",
                                    "chat_id": number
                                })
                                
                                # Wait a bit before replying (respect delay)
                                for _ in range(int(reply_delay * 10)):
                                    if self.status != AgentStatus.ENABLED:
                                        break
                                    await asyncio.sleep(0.1)
                                
                                if self.status != AgentStatus.ENABLED:
                                    break
                                
                                self.session.add_message("status", {"message": "Generating Reply......."})

                                # 📝 Step 2: Extract incoming message
                                history = await AutomationActions.extract_and_format_chat_history(self.session)
                                total_chat_msg = history.get("sender_messages")
                                
                                if not history.get("success"):
                                    incoming_message = ""
                                else:
                                    incoming_message = history.get("formatted_text", "")

                                # 🤖 Step 3: Generate reply using Gemini API
                                reply_message = await self._generate_reply(incoming_message)

                                # 💬 Step 4: Send and close chat
                                self.session.add_message("status", {"message": f"Writing the msg .......&{reply_message}"})
                                send_result = await AutomationActions.SendAndCloseChat(self.session, reply_message)

                            except Exception as e:
                                self.session.add_message("error", {
                                    "agent": "autoreply",
                                    "action": "reply_chat",
                                    "error": str(e)
                                })
                                # Reset current chat on error
                                current_chat_id = None
                                total_chat_msg = None
                                continue

                        # 🕒 Wait between cycles with pause-awareness
                        for _ in range(int(check_interval * 10)):
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
        "message_delay": 3,
        "contacts": ["1234567890", "0987654321"],
        "message_template": "Hi {name}, this is an automated message!",
        "gemini_api_key": "your-api-key",
        "ai_instruction": "Generate a personalized outreach message",
        "use_ai": False,
        "campaign_interval": 60,
        "max_messages_per_cycle": 10
    }
    """
    
    def __init__(self, session: "AutomationSession", config: dict = None):
        super().__init__(AgentType.AUTO_OUTREACH, config)
        self.session = session
        self.sent_contacts = set()  # Track already contacted numbers
        self.current_index = 0
        
    async def _generate_personalized_message(self, contact: str, template: str) -> str:
        """Generate AI-personalized message or use template"""
        
        use_ai = self.config.get("use_ai", False)
        
        if not use_ai:
            # Simply use the template as-is or with basic formatting
            return template.replace("{contact}", contact)
        
        API_KEY = self.config.get("gemini_api_key")
        
        if not API_KEY:
            self.session.add_message("error", {
                "agent": "auto_outreach",
                "action": "initialize_gemini",
                "error": "gemini_api_key is required when use_ai is True"
            })
            return template.replace("{contact}", contact)
        
        ai_instruction = self.config.get("ai_instruction", "")
        
        try:
            prompt = f"{ai_instruction}\n\nContact: {contact}\nTemplate: {template}\n\nGenerate a personalized message:"
            reply = get_chat_reply(prompt, ai_instruction, API_KEY)
            return reply
        except Exception as e:
            self.session.add_message("error", {
                "agent": "auto_outreach",
                "action": "generate_message",
                "error": str(e)
            })
            return template.replace("{contact}", contact)
    
    async def _run(self):
        """Main loop: sends outreach messages to contacts"""
        try:
            message_delay = self.config.get("message_delay", 3)
            campaign_interval = self.config.get("campaign_interval", 60)
            max_messages = self.config.get("max_messages_per_cycle", 10)
            contacts = self.list_of_contact
            message_template = self.messageTemplate
            
            if not contacts:
                self.session.add_message("error", {
                    "agent": "auto_outreach",
                    "error": "No contacts provided in config"
                })
                self.status = AgentStatus.ERROR
                return
            
            if not message_template:
                self.session.add_message("error", {
                    "agent": "auto_outreach",
                    "error": "No message_template provided in config"
                })
                self.status = AgentStatus.ERROR
                return
            
            self.session.add_message("log", {
                "agent": "auto_outreach",
                "event": "started",
                "config": {
                    "total_contacts": len(contacts),
                    "message_delay": message_delay,
                    "campaign_interval": campaign_interval,
                    "use_ai": self.config.get("use_ai", False)
                }
            })
            
            from automation_actions import AutomationActions
            
            while True:
                # Check if paused or disabled
                if self.status != AgentStatus.ENABLED:
                    await asyncio.sleep(0.5)
                    continue
                
                try:
                    messages_sent_this_cycle = 0
                    
                    # Process contacts in batches
                    for contact in contacts:
                        # Check pause state before each message
                        if self.status != AgentStatus.ENABLED:
                            break
                        
                        # Skip already contacted numbers
                        if contact in self.sent_contacts:
                            continue
                        
                        # Check max messages per cycle limit
                        if messages_sent_this_cycle >= max_messages:
                            self.session.add_message("log", {
                                "agent": "auto_outreach",
                                "event": "cycle_limit_reached",
                                "messages_sent": messages_sent_this_cycle
                            })
                            break
                        
                        try:
                            # Open chat with contact
                            self.session.add_message("status", {
                                "message": f"Opening chat with {contact}"
                            })
                            
                            open_result = await AutomationActions.IntializenewChat(
                                self.session, 
                                contact
                            )
                            
                            if not open_result.get("success"):
                                self.session.add_message("error", {
                                    "agent": "auto_outreach",
                                    "action": "open_chat",
                                    "contact": contact,
                                    "error": open_result.get("error", "Failed to open chat")
                                })
                                continue
                            
                            # Highlight the chat in UI
                            self.session.add_message("action", {
                                "action_type": "CHAT_OPENED",
                                "chat_id": "chat_0"
                            })
                            
                            # Wait before sending
                            for _ in range(int(message_delay * 10)):
                                if self.status != AgentStatus.ENABLED:
                                    break
                                await asyncio.sleep(0.1)
                            
                            if self.status != AgentStatus.ENABLED:
                                break
                            
                            # Generate personalized message
                            self.session.add_message("status", {
                                "message": f"Generating message for {contact}"
                            })
                            
                            outreach_message = await self._generate_personalized_message(
                                contact, 
                                message_template
                            )
                            
                            # Send message
                            self.session.add_message("status", {
                                "message": f"Sending message to {contact}"
                            })
                            
                            send_result = await AutomationActions.SendAndCloseChat(
                                self.session, 
                                outreach_message
                            )
                            
                            if send_result.get("success"):
                                self.sent_contacts.add(contact)
                                messages_sent_this_cycle += 1
                                
                                self.session.add_message("log", {
                                    "agent": "auto_outreach",
                                    "event": "message_sent",
                                    "contact": contact,
                                    "total_sent": len(self.sent_contacts)
                                })
                                self.session.add_message("action", {
                                "action_type": "CHAT_OPENED",
                                "chat_id": "chat_0"
                            })
                            else:
                                self.session.add_message("error", {
                                    "agent": "auto_outreach",
                                    "action": "send_message",
                                    "contact": contact,
                                    "error": send_result.get("error", "Failed to send")
                                })
                            
                            # Wait between contacts
                            for _ in range(int(message_delay * 10)):
                                if self.status != AgentStatus.ENABLED:
                                    break
                                await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            self.session.add_message("error", {
                                "agent": "auto_outreach",
                                "action": "process_contact",
                                "contact": contact,
                                "error": str(e)
                            })
                            continue
                    
                    # Check if all contacts have been processed
                    if len(self.sent_contacts) >= len(contacts):
                        self.session.add_message("log", {
                            "agent": "auto_outreach",
                            "event": "campaign_completed",
                            "total_contacts": len(contacts),
                            "successfully_sent": len(self.sent_contacts)
                        })
                        
                        # Reset for next campaign cycle (optional)
                        # self.sent_contacts.clear()
                    
                    # Wait before next cycle
                    self.session.add_message("status", {
                        "message": f"Waiting {campaign_interval}s before next cycle"
                    })
                    
                    for _ in range(int(campaign_interval * 10)):
                        if self.status != AgentStatus.ENABLED:
                            break
                        await asyncio.sleep(0.1)
                    self.stop()
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.error = str(e)
                    self.status = AgentStatus.ERROR
                    self.session.add_message("error", {
                        "agent": "auto_outreach",
                        "error": str(e)
                    })
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            pass
        finally:
            self.session.add_message("log", {
                "agent": "auto_outreach",
                "event": "stopped",
                "total_sent": len(self.sent_contacts)
            })














        


if __name__ == "__main__":
    # Replace with your actual API key
    API_KEY = "AIzaSyBmX1jEygYWngFlDX22Fb0_Vovy0HLRQzU"
    
    # Example chat history
    chat_history = """User: Hello, how are you?
Assistant: I'm doing well, thank you for asking!
User: What can you help me with?"""
    
    # System instruction
    system_inst = "You are a helpful AI assistant. Respond concisely and politely."
    
    try:
        reply = get_chat_reply(chat_history, system_inst, API_KEY)
        print("Generated Reply:")
        print(reply)
    except Exception as e:
        print(f"Error: {e}")




