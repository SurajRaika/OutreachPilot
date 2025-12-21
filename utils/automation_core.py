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
    """Core, low-level Selenium actions for WhatsApp web, including logging of status and errors."""

    # --- Login/State Management ---
    @staticmethod
    async def wait_for_popovers_bucket_and_hide_qr(session: "AutomationSession"):
        """
        Waits for the 'wa-popovers-bucket' element to appear (indicating main app load/login success)
        and sends a HIDE_QR signal to the UI.
        """
        try:
            driver = session.driver
            if not driver:
                return {"success": False, "error": "Driver not initialized"}

            # Wait up to 60 seconds for the element to be present
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "wa-popovers-bucket"))
            )

            # Element found, user is likely logged in and QR screen is gone
            # Sending the action message as requested by the user
            session.add_message("action", {
                "action_type": "HIDE_QR",
                "message": "QR code ready — ask user to scan"
            })
            session.add_message("status", {"message": "User login confirmed "})
            return {"success": True, "state": "login_confirmed"}

        except TimeoutException:
            session.add_message("log", {"message": "Timeout waiting for wa-popovers-bucket (login may have failed or taken too long)."})
            return {"success": False, "error": "Timeout waiting for login confirmation element."}
        except Exception as e:
            session.add_message("error", {"action": "wait_login_element", "error": str(e)})
            return {"success": False, "error": f"Error waiting for popovers bucket: {e}"}


    @staticmethod
    async def check_login_state(session: "AutomationSession") -> dict:
        """
        Check the current WhatsApp Web state and log the status.
        States: logging_in (QR visible), logged_in, unknown.
        """
        try:
            driver = session.driver
            if not driver:
                session.add_message("status", {"message": "Driver not initialized"})
                return {"success": False, "error": "Driver not initialized"}

            # Use a very short wait time (1 second) to quickly check state without blocking much
            
            # 1. 🟡 Check for QR/Logging in screen (presence of canvas)
            try:
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
                )
                # Logging for QR state
                session.add_message("status", {"message": "User logged out"})
                session.add_message("action", {
                    "action_type": "SHOW_QR",
                    "message": "QR code ready — ask user to scan"
                })
                return {"success": True, "state": "logging_in"} 
            except TimeoutException:
                pass


            # 2. 🟢 Check for "New Chat Icon" → user is logged in
            try:
                WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-icon='new-chat-outline']"))
                )
                session.add_message("status", {"message": "User logged in"})
                return {"success": True, "state": "logged_in"}
            except TimeoutException:
                pass

            # 3. ⚪ Unknown state (fallback)
            session.add_message("status", {"message": "Unable to determine login state"})
            return {"success": True, "state": "unknown"}

        except Exception as e:
            session.add_message("log", {"message": f"Login state check failed: {e}"})
            return {"success": False, "error": f"Login state check failed: {e}"}

    @staticmethod
    async def get_qr_code(session: "AutomationSession") -> dict:
        """Extracts the QR code (base64) from the canvas element and logs success/failure."""
        try:
            if not session.driver:
                session.add_message("status", {"message": "Driver not initialized"})
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

            session.add_message("log", {"message": "QR code extracted"})
            async def background_check():
                await AutomationCore.wait_for_popovers_bucket_and_hide_qr(session)
            asyncio.create_task(background_check())

            return {"success": True, "qr_code": base64_data}

        except Exception as e:
            session.add_message("log", {"message": f"Failed to get QR code: {e}"})
            return {"success": False, "error": f"Failed to get QR code: {e}"}
            
    # --- Chat Actions ---

    @staticmethod
    async def InitializeNewChat(session: "AutomationSession", number: str) -> dict:
        """Opens a new WhatsApp chat with the given number, logging the process."""
        try:
            # --- Pre-check ---
            if not session.driver:
                session.add_message("status", {"message": "Driver not initialized"})
                return {"success": False, "error": "Driver not initialized"}

            wa_link = f"https://api.whatsapp.com/send/?phone={number}"
            session.add_message("status", {"message": f"Opening chat with {number}"})

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
                session.add_message("status", {"message": f"Chat opened with {number}"})
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

                    # Logging for invalid number
                    session.add_message("status", {"message": f"{number} is not on WhatsApp"})
                    session.add_message("action", {
                        "action_type": "PROMPT_USER",
                        "message": f"The number {number} is not on WhatsApp."
                    })
                    return {"success": False, "state": "invalid_number", "message": f"Number {number} is not on WhatsApp or chat failed to open."}

                except TimeoutException:
                    # Logging for chat load failure
                    session.add_message("status", {"message": "Chat not found or still loading"})
                    return {"success": False, "state": "chat_load_failed", "message": "Chat not found, still loading, or WhatsApp state is unknown."}

        except Exception as e:
            session.add_message("log", {"message": f"Failed to open chat: {e}"})
            return {"success": False, "error": f"Failed to open chat: {e}"}


    @staticmethod
    async def SendMessage(session: "AutomationSession", msg: str) -> dict:
        """Send a message in the currently open WhatsApp chat, logging the result."""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}

            CHAT_INPUT_SELECTOR = "div[contenteditable='true'][aria-placeholder='Type a message']"

            # Focus on message input and type the message
            input_box = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, CHAT_INPUT_SELECTOR))
            )
            ActionChains(session.driver).move_to_element(input_box).click().send_keys(msg).perform()
            
            # Use ENTER key to send message
            ActionChains(session.driver).send_keys(Keys.ENTER).perform()
            
            session.add_message("action", {"type": "send_message", "state": "sent"})
            await asyncio.sleep(1) 
            return {"success": True, "state": "message_sent", "message": msg}

        except Exception as e:
            session.add_message("error", {"action": "send_message", "error": str(e)})
            return {"success": False, "error": f"Failed to send message: {e}"}

    @staticmethod
    async def CloseCurrentChat(session: "AutomationSession") -> dict:
        """Closes the currently open WhatsApp chat via context menu and keyboard actions, logging the result."""
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

            session.add_message("log", {"action": "close_chat", "state": "closed"})
            return {"success": True, "state": "chat_closed"}

        except Exception as e:
            session.add_message("error", {"action": "close_chat", "error": str(e)})
            return {"success": False, "error": f"Failed to close chat: {e}"}