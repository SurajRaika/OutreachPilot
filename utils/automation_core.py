# automation_core.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from typing import TYPE_CHECKING
import asyncio

# Assuming 'AutomationSession' is defined in 'session.py'
if TYPE_CHECKING:
    from session import AutomationSession

class AutomationCore:
    """Core, low-level Selenium actions for WhatsApp web."""

    # --- Login/State Management ---

    @staticmethod
    async def check_login_state(session: "AutomationSession") -> dict:
        """Check if the user is logged in or not. The UI-facing layer (AutomationActions) handles the messaging/notifications."""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}

            # 🟡 Check for "Steps to log in" → user is logged out (Login prompt visible)
            try:
                WebDriverWait(session.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.x579bpy.xo1l8bm.xggjnk3.x1hql6x6"))
                )
                return {"success": True, "state": "logged_out"}
            except TimeoutException:
                pass

            # 🟢 Check for "New Chat Icon" → user is logged in (Chat interface visible)
            try:
                WebDriverWait(session.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-icon='new-chat-outline']"))
                )
                return {"success": True, "state": "logged_in"}
            except TimeoutException:
                pass

            # ⚪ Unknown state
            return {"success": True, "state": "unknown"}

        except Exception as e:
            return {"success": False, "error": f"Login state check failed: {e}"}

    @staticmethod
    async def get_qr_code(session: "AutomationSession") -> dict:
        """Extracts the QR code (base64) from the canvas element."""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            # Wait for QR canvas
            canvas = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            
            # Extract base64 image data via JavaScript
            base64_data = session.driver.execute_script(
                "return arguments[0].toDataURL('image/png');",
                canvas
            )

            return {"success": True, "qr_code": base64_data}

        except Exception as e:
            return {"success": False, "error": f"Failed to get QR code: {e}"}
            
    # --- Chat Actions ---

    @staticmethod
    async def InitializeNewChat(session: "AutomationSession", number: str) -> dict:
        """Opens a new WhatsApp chat with the given number. Returns once the chat input is visible or an error occurs."""
        try:
            # --- Pre-check ---
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}

            wa_link = f"https://api.whatsapp.com/send/?phone={number}"

            # --- Inject JS to open WhatsApp chat in new tab/window ---
            script = f"""
                (function() {{
                    const link = document.createElement('a');
                    link.href = '{wa_link}';
                    link.target = '_blank';
                    link.id = 'hidden-whatsapp-link';
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    setTimeout(() => link.click(), 100); 
                    setTimeout(() => link.remove(), 2000); // Cleanup
                }})();
            """
            session.driver.execute_script(script)
            
            await asyncio.sleep(2) 

            # --- Wait for chat input box or error dialog ---
            CHAT_INPUT_SELECTOR = "div[contenteditable='true'][aria-placeholder='Type a message']"
            
            try:
                WebDriverWait(session.driver, 8).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, CHAT_INPUT_SELECTOR))
                )
                return {"success": True, "state": "chat_opened", "url": wa_link}

            except TimeoutException:
                # ❌ Try to detect invalid number dialog 
                try:
                    invalid_popup = WebDriverWait(session.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'invalid')]"))
                    )
                    
                    # Click 'OK' to dismiss if found
                    try:
                        ok_button = invalid_popup.find_element(By.XPATH, ".//span[normalize-space()='OK']")
                        session.driver.execute_script("arguments[0].click();", ok_button)
                    except:
                        pass

                    return {"success": False, "state": "invalid_number", "message": f"Number {number} is not on WhatsApp or chat failed to open."}

                except TimeoutException:
                    return {"success": False, "state": "chat_load_failed", "message": "Chat not found, still loading, or WhatsApp state is unknown."}

        except Exception as e:
            return {"success": False, "error": f"Failed to open chat: {e}"}


    @staticmethod
    async def SendMessage(session: "AutomationSession", msg: str) -> dict:
        """Send a message in the currently open WhatsApp chat."""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}

            CHAT_INPUT_SELECTOR = "div[contenteditable='true'][aria-placeholder='Type a message']"

            # ✅ Focus on message input and type the message
            input_box = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, CHAT_INPUT_SELECTOR))
            )
            # Use ActionChains to click and send keys in one go
            ActionChains(session.driver).move_to_element(input_box).click().send_keys(msg).perform()
            
            # Use ENTER key to send message (more reliable than finding the send button)
            ActionChains(session.driver).send_keys(Keys.ENTER).perform()
            
            await asyncio.sleep(1) 
            return {"success": True, "state": "message_sent", "message": msg}

        except Exception as e:
            return {"success": False, "error": f"Failed to send message: {e}"}

    @staticmethod
    async def CloseCurrentChat(session: "AutomationSession") -> dict:
        """Closes the currently open WhatsApp chat via context menu and keyboard actions."""
        try:
            driver = session.driver
            if not driver:
                return {"success": False, "error": "Driver not initialized"}

            CHAT_INPUT_SELECTOR = "div[contenteditable='true'][aria-placeholder='Type a message']"

            # Wait for chat input (base element to calculate offset)
            target_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, CHAT_INPUT_SELECTOR))
            )

            # Move slightly above and right-click to open context menu
            X_OFFSET = 0
            Y_OFFSET = -100
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(target_element, X_OFFSET, Y_OFFSET)
            actions.context_click().perform()

            await asyncio.sleep(1)

            # Press Down Arrow 6 times (targetting 'Close chat')
            actions = ActionChains(driver)
            for _ in range(6):
                actions.send_keys(Keys.ARROW_DOWN)
            actions.perform()

            await asyncio.sleep(1)

            # Press Enter to select the option
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER).perform()

            await asyncio.sleep(0.5)

            return {"success": True, "state": "chat_closed"}

        except Exception as e:
            return {"success": False, "error": f"Failed to close chat: {e}"}