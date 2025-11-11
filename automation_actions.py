from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, List , TYPE_CHECKING
from session import AutomationSession
import asyncio
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from utils.automation_core import AutomationCore



if TYPE_CHECKING:
    from session import AutomationSession
class AutomationActions:
    def __init__(self):
        # this is an instance variable (shared by methods of THIS object)
        self.CHAT_INPUT_SELECTOR="div[contenteditable='true'][aria-placeholder='Type a message']"

    """Handles automation actions - simplified for WhatsApp automation"""
    
    @staticmethod
    async def initialize(session: "AutomationSession", url: str = "https://web.whatsapp.com/", headless: bool = True) -> dict:
        """
        Initialize browser and navigate to WhatsApp Web.
        This only handles the driver setup and navigation, NOT login detection.
        Also runs background check for login state and handles QR extraction.
        """
        try:
            if not session.driver:
                session.create_driver(headless=headless)

            session.driver.get(url)

            session.add_message("status", {
                "message": "WhatsApp session initialized successfully",
            })

            result = {
                "success": True,
                "title": session.driver.title,
                "url": session.driver.current_url
            }

            print(f"✅ Browser initialized — Title: {result['title']}\n")

            session.add_message("action", {
                            "action_type": "SHOW_QR",
                            "message": "QR code ready — ask user to scan",
                            
                        })

            async def background_check():
                await AutomationActions.check_login_state(session)
            asyncio.create_task(background_check())
            
            return result

        except Exception as e:
            session.add_message("error", {"action": "navigate", "error": str(e)})
            print(f"❌ Failed to initialize: {e}")
            return {"success": False, "error": str(e)}


    @staticmethod
    async def check_login_state(session: AutomationSession) -> dict:
        """Check if the user is logged in or not."""
        try:
            if not session.driver:
                session.add_message("status", {"message": "Driver not initialized"})
                return {"success": False, "error": "Driver not initialized"}

            # 🟡 Check for "Steps to log in" → user is logged out
            try:
                WebDriverWait(session.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.x579bpy.xo1l8bm.xggjnk3.x1hql6x6"))
                )
                session.add_message("status", {"message": "User logged out"})
                session.add_message("action", {
                    "action_type": "SHOW_QR",
                    "message": "QR code ready — ask user to scan"
                })
                return {"success": True, "state": "logged_out"}
            except TimeoutException:
                pass

            # 🟢 Check for "New Chat Icon" → user is logged in
            try:
                WebDriverWait(session.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-icon='new-chat-outline']"))
                )
                session.add_message("status", {"message": "User logged in"})
                return {"success": True, "state": "logged_in"}
            except TimeoutException:
                pass

            # 🟣 (Optional) Chats downloading phase
            try:
                WebDriverWait(session.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "your-chats-downloading-selector"))
                )
                session.add_message("status", {"message": "Chats downloading"})
                return {"success": True, "state": "downloading_chats"}
            except TimeoutException:
                pass

            # ⚪ Unknown state
            session.add_message("status", {"message": "Unable to determine login state"})
            return {"success": True, "state": "unknown"}

        except Exception as e:
            session.add_message("log", {"message": f"Login state check failed: {e}"})
            return {"success": False, "error": str(e)}


    @staticmethod
    async def get_qr_code_if_logout(session: AutomationSession) -> dict:
        """Get QR code only if user is logged out."""
        try:
            if not session.driver:
                session.add_message("status", {"message": "Driver not initialized"})
                return {"success": False, "error": "Driver not initialized"}
            
            # Check current login state
            login_state = await AutomationActions.check_login_state(session)
            if login_state.get("state") != "logged_out":
                session.add_message("status", {"message": "User already logged in"})
                return {"success": False, "message": "User already logged in"}
            
            # Wait for QR canvas and extract base64 image
            canvas = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            base64_data = session.driver.execute_script(
                "return arguments[0].toDataURL('image/png');",
                canvas
            )

            # Send minimal log + action messages
            session.add_message("log", {"message": "QR code extracted"})
            

            return {"success": True, "qr_code": base64_data, "state": "logged_out"}

        except Exception as e:
            session.add_message("log", {"message": f"Failed to get QR code: {e}"})
            return {"success": False, "error": str(e)}



    @staticmethod
    async def IntializenewChat(session: AutomationSession, number: int, msg: str = "") -> dict:
        """Open a new WhatsApp chat with the given number and optionally send a message."""
        try:
            # --- Pre-check ---
            if not session.driver:
                session.add_message("status", {"message": "Driver not initialized"})
                return {"success": False, "error": "Driver not initialized"}

            wa_link = f"https://api.whatsapp.com/send/?phone={number}"
            session.add_message("status", {"message": f"Opening chat with {number}"})

            # --- Inject JS to open WhatsApp chat ---
            script = f"""
                (function() {{
                    const link = document.createElement('a');
                    link.href = '{wa_link}';
                    link.target = '_blank';
                    link.id = 'hidden-whatsapp-link';
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    setTimeout(() => link.click(), 1000);
                }})();
            """
            session.driver.execute_script(script)
            await asyncio.sleep(1.2)

            # --- Wait for chat input box ---
            try:
                WebDriverWait(session.driver, 10).until(
                    EC.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        "div[contenteditable='true'][aria-placeholder='Type a message']"
                    ))
                )
                session.add_message("status", {"message": f"Chat opened with {number}"})

                # 📨 Send message if provided
                if msg.strip():
                    try:
                        message_box = WebDriverWait(session.driver, 10).until(
                            EC.visibility_of_element_located((
                                By.XPATH,
                                "/html/body/div[1]/div/div/div[5]/div/footer/div[1]/div/span[2]/div/div[2]/div[1]/div/div[2]"
                            ))
                        )
                        ActionChains(session.driver).move_to_element(message_box).click().perform()
                        ActionChains(session.driver).send_keys(msg).perform()

                        send_btn = session.driver.find_element(
                            By.XPATH,
                            "/html/body/div[1]/div/div/div[5]/div/footer/div[1]/div/span[2]/div/div[2]/div[2]/button"
                        )
                        send_btn.click()

                        session.add_message("log", {"message": f"Message sent to {number}"})
                        return {"success": True, "state": "message_sent", "url": wa_link}

                    except Exception as e:
                        session.add_message("log", {"message": f"Chat opened but message not sent: {e}"})
                        return {"success": True, "state": "chat_opened_but_not_sent", "url": wa_link}

                # 🟢 Chat opened but no message
                return {"success": True, "state": "chat_opened", "url": wa_link}

            except TimeoutException:
                # ❌ Try to detect invalid number dialog
                try:
                    invalid_popup = WebDriverWait(session.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'invalid')]"))
                    )
                    session.add_message("status", {"message": f"{number} is not on WhatsApp"})
                    session.add_message("action", {
                        "action_type": "PROMPT_USER",
                        "message": f"The number {number} is not on WhatsApp."
                    })

                    try:
                        ok_button = invalid_popup.find_element(By.XPATH, ".//span[normalize-space()='OK']")
                        session.driver.execute_script("arguments[0].click();", ok_button)
                    except Exception:
                        pass

                    return {"success": False, "state": "invalid_number"}

                except TimeoutException:
                    session.add_message("status", {"message": "Chat not found or still loading"})
                    return {"success": True, "state": "unknown"}

        except Exception as e:
            session.add_message("log", {"message": f"Failed to open chat: {e}"})
            return {"success": False, "error": str(e)}


    @staticmethod
    async def SendMessage(session: AutomationSession, msg: str) -> dict:
        """Send a message in the currently open WhatsApp chat."""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}

            # ✅ Focus on message input
            input_box = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[contenteditable='true'][aria-placeholder='Type a message']"
                ))
            )
            ActionChains(session.driver).move_to_element(input_box).click().perform()
            await asyncio.sleep(0.5)
            input_box.send_keys(msg)
            await asyncio.sleep(0.5)
            session.add_message("log", {"action": "focus_and_type", "state": "done"})

            # ✅ Find and click the send button (3-level parent)
            send_button = session.driver.execute_script("""
                const input = arguments[0];
                let parent = input;
                for (let i = 0; i < 3; i++) if (parent.parentElement) parent = parent.parentElement;
                return parent.querySelector("div[role='button'][aria-label='Send']");
            """, input_box)

            if send_button:
                session.driver.execute_script("arguments[0].click();", send_button)
                session.add_message("action", {"type": "send_message", "state": "sent"})
                return {"success": True, "state": "message_sent", "message": msg}

            session.add_message("error", {"action": "send_message", "error": "Send button not found"})
            return {"success": False, "error": "Send button not found"}

        except Exception as e:
            session.add_message("error", {"action": "send_message", "error": str(e)})
            return {"success": False, "error": str(e)}

    @staticmethod
    async def CloseCurrentChat(session) -> dict:
        """
        Closes the currently open WhatsApp chat.

        Steps:
        1. Find the chat input area to locate a known chat region.
        2. Move slightly above it and right-click to open the chat context menu.
        3. Wait 1 second, press the down arrow 6 times, wait 1 second, and press Enter to close the chat.
        """
        try:
            driver = session.driver
            if not driver:
                return {"success": False, "error": "Driver not initialized"}

            # ✅ Wait for chat input (base element to calculate offset)
            target_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[contenteditable='true'][aria-placeholder='Type a message']"
                ))
            )

            # ✅ Move slightly above and right-click to open context menu
            X_OFFSET = 0
            Y_OFFSET = -100
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(target_element, X_OFFSET, Y_OFFSET)
            actions.context_click().perform()

            # ✅ Wait for menu to open
            await asyncio.sleep(1)

            # ✅ Press Down Arrow 6 times
            actions = ActionChains(driver)
            for _ in range(6):
                actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()

            await asyncio.sleep(1)

            # ✅ Press Enter to select the option
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER).perform()

            await asyncio.sleep(0.5)

            session.add_message("log", {"action": "close_chat", "state": "closed"})
            return {"success": True, "state": "chat_closed"}

        except Exception as e:
            session.add_message("error", {"action": "close_chat", "error": str(e)})
            return {"success": False, "error": str(e)}







                
# Standalone testing
if __name__ == "__main__":
    import asyncio
    from session import AutomationSession

    async def main():
        """Test WhatsApp automation initialization and login state."""
        print("🧪 WhatsApp Automation Test\n")

        # Step 1️⃣: Create a new session
        session = AutomationSession("test-001", "TestProfile")

        # Step 2️⃣: Initialize browser (no login check yet)
        print("1️⃣ Initializing browser and navigating to WhatsApp Web...")
        init_result = await AutomationActions.initialize(session, "https://web.whatsapp.com/", headless=False)
        if not init_result.get("success"):
            print(f"❌ Failed to initialize: {init_result.get('error')}")
            return
        print(f"✅ Browser initialized — Title: {init_result.get('title')}\n")

        # Step 3️⃣: Check login state
        print("2️⃣ Checking login state...")
        state = await AutomationActions.check_login_state(session)
        print(f"🟡 State: {state.get('state')} - {state.get('message')}\n")

        # Step 4️⃣: Handle based on login state
        if state.get("state") == "logged_out":
            print("📸 User is logged out — fetching QR code...")
            qr_result = await AutomationActions.get_qr_code_if_logout(session)
            if qr_result.get("success"):
                print("✅ QR code successfully extracted (base64 truncated):")
                print(qr_result.get("qr_code")[:100] + "...")  # Only print first 100 chars
            else:
                print(f"❌ Failed to extract QR: {qr_result.get('error')}")
        elif state.get("state") == "logged_in":
            print("✅ User is already logged in and ready for actions!")
        else:
            print("⚠️ Unable to determine login state — please check manually.")


        # Step 6️⃣: Test chat initialization (now passing session correctly)
        chat_result = await AutomationActions.IntializenewChat(session, "918058201385", "")
        print(f"💬 Chat Result: {chat_result}\n")
        asda = await AutomationActions.SendMessage(session, "hy")
        seesion= await AutomationActions.CloseCurrentChat(session)
        chat_result = await AutomationActions.IntializenewChat(session, "919799105754", "")
        asda = await AutomationActions.SendMessage(session, "Hello ")
        seesion= await AutomationActions.CloseCurrentChat(session)

        # Step 5️⃣: Cleanup
        print("\please wait to close the browser...")
        input()
        session.cleanup()
        print("✅ Browser closed and session cleaned up.")

    asyncio.run(main())


