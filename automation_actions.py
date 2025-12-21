from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, List , TYPE_CHECKING
from session import AutomationSession
import asyncio
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys



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



                async def background_check():
                    await AutomationActions.check_login_state(session)
                asyncio.create_task(background_check())
                
                return result

            except Exception as e:
                session.add_message("error", {"action": "navigate", "error": str(e)})
                print(f"❌ Failed to initialize: {e}")
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
        async def get_whatsapp_live_state(session: "AutomationSession", target_state: str):
            """
            Instantly checks only the requested WhatsApp Web state without waiting.

            target_state options:
                - "qr_visible"
                - "loading_chats"
                - "logged_in"
            """
            try:
                driver = session.driver
                if not driver:
                    return {"success": False, "error": "Driver not initialized"}

                # Switch-like state checks
                match target_state:

                    case "qr_visible":
                        try:
                            driver.find_element(By.TAG_NAME, "canvas")
                            return {"success": True, "state": "qr_visible"}
                        except NoSuchElementException:
                            return {"success": False, "state": "not_found"}

                    case "loading_chats":
                        try:
                            driver.find_element(
                                By.XPATH,
                                "//div[contains(@class, 'x1c3i2sq') and text()='Loading your chats']"
                            )
                            session.add_message("action", {"action_type": "SHOW_ADVANCE"})

                            return {"success": True, "state": "loading_chats"}
                        except NoSuchElementException:
                            return {"success": False, "state": "not_found"}

                    case "logged_in":
                        # logged in means: no QR + no loading screen
                        try:
                            driver.find_element(By.TAG_NAME, "canvas")  # QR visible = not logged in
                            return {"success": False, "state": "qr_visible"}
                        except NoSuchElementException:
                            try:
                                driver.find_element(
                                    By.XPATH,
                                    "//div[contains(@class, 'x1c3i2sq') and text()='Loading your chats']"
                                )
                                return {"success": False, "state": "loading_chats"}
                            except NoSuchElementException:
                                session.add_message("action", {"action_type": "SHOW_ADVANCE"})

                                return {"success": True, "state": "logged_in"}

                    case _:
                        return {"success": False, "error": f"Unknown target_state '{target_state}'"}

            except Exception as e:
                session.add_message("error", {"action": "check_live_state", "error": str(e)})
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
                    session.add_message("action", {"action_type": "SHOW_ADVANCE"})

                    
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
            try:
                if not session.driver:
                    return {"success": False, "error": "Driver not initialized"}

                # Validate connection
                try:
                    session.driver.execute_script("return 1")
                except:
                    return {"success": False, "error": "WebDriver session lost"}

                # Locate input box
                input_box = WebDriverWait(session.driver, 10).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "div[contenteditable='true'][aria-placeholder='Type a message']"
                    ))
                )

                ActionChains(session.driver).move_to_element(input_box).click().perform()
                input_box.send_keys(msg)

                # ---- METHOD 1: Try clicking Send button ----
                send_button = session.driver.execute_script("""
                    const input = arguments[0];
                    let parent = input;
                    for (let i = 0; i < 5; i++) {
                        if (parent.parentElement) parent = parent.parentElement;
                    }
                    return parent.querySelector("div[role='button'][aria-label='Send']");
                """, input_box)

                if send_button:
                    session.driver.execute_script("arguments[0].click();", send_button)
                    return {
                        "success": True,
                        "state": "message_sent",
                        "method": "send_button",
                        "message": msg
                    }

                # ---- METHOD 2: Fallback to ENTER key ----
                input_box.send_keys(Keys.ENTER)
                return {
                    "success": True,
                    "state": "message_sent",
                    "method": "enter_key",
                    "message": msg
                }

            except Exception as e:
                return {"success": False, "error": f"Exception: {e}"}





        @staticmethod
        async def CloseCurrentChat(session) -> dict:
                """
                Closes the currently open WhatsApp chat with multiple fallback strategies.

                Steps:
                1. Check if chat is already closed by looking for input box
                2. Try context menu method with different Y offsets
                3. Try ESC key multiple times
                4. Combine strategies until chat is confirmed closed
                """
                try:
                    driver = session.driver
                    if not driver:
                        return {"success": False, "error": "Driver not initialized"}

                    max_attempts = 5
                    y_offsets = [-100, -150, -80, -120, -200]
                    
                    for attempt in range(max_attempts):
                        # ✅ Check if chat is already closed
                        try:
                            input_box = WebDriverWait(driver, 2).until(
                                EC.presence_of_element_located((
                                    By.CSS_SELECTOR,
                                    "div[contenteditable='true'][aria-placeholder='Type a message']"
                                ))
                            )
                            # Chat is still open, continue trying to close it
                        except:
                            # Input box not found - chat is closed!
                            session.add_message("log", {"action": "close_chat", "state": "closed", "attempts": attempt + 1})
                            return {"success": True, "state": "chat_closed", "attempts": attempt + 1}

                        # Strategy 1: Context menu method (attempts 0-2)
                        if attempt < 3:
                            try:
                                target_element = WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((
                                        By.CSS_SELECTOR,
                                        "div[contenteditable='true'][aria-placeholder='Type a message']"
                                    ))
                                )

                                # Use different Y offset for each attempt
                                X_OFFSET = 0
                                Y_OFFSET = y_offsets[attempt]
                                
                                actions = ActionChains(driver)
                                actions.move_to_element_with_offset(target_element, X_OFFSET, Y_OFFSET)
                                actions.context_click().perform()

                                await asyncio.sleep(1)

                                # Press Down Arrow 6 times
                                actions = ActionChains(driver)
                                for _ in range(6):
                                    actions.send_keys(Keys.ARROW_DOWN)
                                actions.perform()

                                await asyncio.sleep(1)

                                # Press Enter
                                actions = ActionChains(driver)
                                actions.send_keys(Keys.ENTER).perform()

                                await asyncio.sleep(1)
                                
                            except Exception as e:
                                session.add_message("log", {"action": "close_chat", "attempt": attempt + 1, "strategy": "context_menu", "error": str(e)})
                        
                        # Strategy 2: ESC key method (attempts 3-4)
                        else:
                            try:
                                actions = ActionChains(driver)
                                # Press ESC multiple times
                                esc_presses = 3 if attempt == 3 else 5
                                for _ in range(esc_presses):
                                    actions.send_keys(Keys.ESCAPE)
                                actions.perform()
                                
                                await asyncio.sleep(1)
                                
                            except Exception as e:
                                session.add_message("log", {"action": "close_chat", "attempt": attempt + 1, "strategy": "esc_key", "error": str(e)})
                        
                        # Brief pause before next check
                        await asyncio.sleep(0.5)

                    # Final check after all attempts
                    try:
                        input_box = WebDriverWait(driver, 2).until(
                            EC.presence_of_element_located((
                                By.CSS_SELECTOR,
                                "div[contenteditable='true'][aria-placeholder='Type a message']"
                            ))
                        )
                        # Still open after all attempts
                        session.add_message("error", {"action": "close_chat", "state": "failed", "attempts": max_attempts})
                        return {"success": False, "error": "Failed to close chat after all attempts"}
                    except:
                        # Successfully closed
                        session.add_message("log", {"action": "close_chat", "state": "closed", "attempts": max_attempts})
                        return {"success": True, "state": "chat_closed", "attempts": max_attempts}

                except Exception as e:
                    session.add_message("error", {"action": "close_chat", "error": str(e)})
                    return {"success": False, "error": str(e)}



        @staticmethod
        async def SendAndCloseChat(session: AutomationSession, msg: str) -> dict:
            """
            Initiates a WhatsApp chat, sends a message with retry, and closes the chat.
            Retries sending message up to 3 times if it fails.
            """
            results = {
                "initialize": None,
                "send": None,
                "close": None
            }

            send_result = None

            try:
                # Step 1️⃣: Send the message with retry
                session.add_message("log", {"action": "send_message",  "state": "attempting"})
                
                send_result = await AutomationActions.SendMessage(session, msg)
                results["send"] = send_result

                if send_result.get("success"):
                    session.add_message("log", {"action": "send_message", "state": "success"})
                else:
                    session.add_message("warning", {"action": "send_message", "state": "failed", "error": send_result.get("error")})
                    

                # If after all attempts still failed
                if not send_result or not send_result.get("success"):
                    return {
                        "success": False,
                        "step": "send_message",
                        "details": send_result,
                        "error": send_result.get("error", "Message not sent after retries"),
                    }

                session.add_message("log", {"action": "sequence", "step": "message_sent"})

    

                # ✅ Complete
                return {
                    "success": True,
                    "state": "complete",
                    "steps": results,
                    "message": msg
                }

            except Exception as e:
                session.add_message("error", {"action": "send_and_close_chat", "error": str(e)})
                return {
                    "success": False,
                    "error": str(e),
                    "steps": results
                }


        @staticmethod
        async def get_chats_list(session: "AutomationSession") -> dict:
            """
            Get list of WhatsApp chats with their info and IDs using pure Selenium.
            Returns chat ranking, pinned status, title, recent message, and chat ID.
            """
            try:
                if not session.driver:
                    session.add_message("error", {"message": "Driver not initialized"})
                    return {"success": False, "error": "Driver not initialized"}
                
                # Wait for chat list to be present
                try:
                    chat_list = WebDriverWait(session.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Chat list"]'))
                    )
                except TimeoutException:
                    session.add_message("error", {"message": "Chat list not found"})
                    return {"success": False, "error": "Chat list not found - user may not be logged in"}
                
                # Get all chat rows
                try:
                    chat_rows = chat_list.find_elements(By.CSS_SELECTOR, '[role="row"]')
                except NoSuchElementException:
                    session.add_message("error", {"message": "No chat rows found"})
                    return {"success": False, "error": "No chat rows found"}
                
                if len(chat_rows) == 0:
                    session.add_message("status", {"message": "Chat list is empty"})
                    return {"success": True, "chats": [], "total_count": 0}
                
                chats = []
                
                for index, row in enumerate(chat_rows):
                    try:
                        # 1. Get the Title (Contact Name/Number)
                        title = "Title Not Found"
                        try:
                            title_element = row.find_element(By.CSS_SELECTOR, '[title]')
                            title = title_element.get_attribute('title').strip()
                        except NoSuchElementException:
                            pass
                        
                        # 2. Get the Recent Message/Description
                        description = "Description Not Found"
                        try:
                            # Try primary selector
                            message_span = row.find_element(By.CSS_SELECTOR, 'div[role="gridcell"]:nth-child(2) + div span[dir="ltr"]')
                            description = message_span.text.strip()
                        except NoSuchElementException:
                            try:
                                # Fallback selector
                                fallback_message = row.find_element(By.CSS_SELECTOR, '.x1iyjqo2[dir="ltr"]')
                                description = fallback_message.text.strip()
                            except NoSuchElementException:
                                pass
                        
                        # 3. Get the Ranking Number
                        ranking = index + 1
                        
                        # 4. Check for Pinned Status
                        is_pinned = False
                        try:
                            row.find_element(By.CSS_SELECTOR, '[aria-label="Pinned chat"]')
                            is_pinned = True
                        except NoSuchElementException:
                            pass
                        
                        # 5. Get Chat ID from href
                        chat_id = None
                        try:
                            link_element = row.find_element(By.CSS_SELECTOR, 'a[href*="web.whatsapp.com"]')
                            href = link_element.get_attribute('href')
                            
                            # Extract chat ID using regex pattern
                            import re
                            match = re.search(r'[0-9]+@[cgs]\.us', href)
                            if match:
                                chat_id = match.group(0)
                        except NoSuchElementException:
                            pass
                        
                        # Fallback: try data-id attribute
                        if not chat_id:
                            try:
                                chat_id = row.get_attribute('data-id')
                            except:
                                pass
                        
                        # Last resort fallback
                        if not chat_id:
                            chat_id = f"chat_{index}"
                        
                        chats.append({
                            "id": chat_id,
                            "ranking": ranking,
                            "isPinned": is_pinned,
                            "title": title,
                            "recentMessage": description,
                        })
                        
                    except Exception as e:
                        session.add_message("error", {
                            "action": "parse_chat_row",
                            "index": index,
                            "error": str(e)
                        })
                        continue
                
                
                
                return {
                    "success": True,
                    "chats": chats,
                    "total_count": len(chats)
                }
                
            except Exception as e:
                session.add_message("error", {
                    "action": "get_chats_list",
                    "error": str(e)
                })
                return {"success": False, "error": str(e)}

        @staticmethod
        def extract_chat_id_from_row(row, index: int) -> str:
            """
            Extract chat ID from a chat row element using Selenium.
            This ensures consistent ID extraction across all methods.
            
            Args:
                row: Selenium WebElement representing a chat row
                index: Row index as fallback
            
            Returns:
                Chat ID string
            """
            import re
            
            # Primary method: Extract from href
            try:
                link_element = row.find_element(By.CSS_SELECTOR, 'a[href*="web.whatsapp.com"]')
                href = link_element.get_attribute('href')
                # Match WhatsApp chat ID format: number@c.us (contact) or number@g.us (group)
                match = re.search(r'[0-9]+@[cgs]\.us', href)
                if match:
                    return match.group(0)
            except NoSuchElementException:
                pass
            
            # Fallback 1: Check data-id attribute
            try:
                data_id = row.get_attribute('data-id')
                if data_id:
                    return data_id
            except:
                pass
            
            # Fallback 2: Generate based on title (less reliable but better than index)
            try:
                title_element = row.find_element(By.CSS_SELECTOR, '[title]')
                title = title_element.get_attribute('title').strip()
                if title:
                    safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)
                    return f"chat_{safe_title}_{index}"
            except NoSuchElementException:
                pass
            
            # Last resort: Use index
            return f"chat_index_{index}"

        @staticmethod
        async def verify_chat_ids(session: "AutomationSession") -> dict:
            """
            Verify that chat IDs are consistent across multiple calls using Selenium.
            Useful for debugging and ensuring reliability.
            """
            try:
                if not session.driver:
                    return {"success": False, "error": "Driver not initialized"}
                
                # Get all chats using Selenium
                all_chats_result = await AutomationActions.get_chats_list(session)
                if not all_chats_result["success"]:
                    return all_chats_result
                
                # Get unread chat IDs using Selenium
                try:
                    chat_list = WebDriverWait(session.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Chat list"]'))
                    )
                    chat_rows = chat_list.find_elements(By.CSS_SELECTOR, '[role="row"]')
                    
                    unread_ids = []
                    for index, row in enumerate(chat_rows):
                        try:
                            # Check if chat is unread
                            unread_elements = row.find_elements(By.CSS_SELECTOR, '[aria-label*="unread message"]')
                            is_unread = False
                            for elem in unread_elements:
                                aria_label = elem.get_attribute('aria-label')
                                if aria_label and ('unread message' in aria_label or 'unread messages' in aria_label):
                                    is_unread = True
                                    break
                            
                            if is_unread:
                                chat_id = AutomationActions.extract_chat_id_from_row(row, index)
                                unread_ids.append(chat_id)
                        except:
                            continue
                            
                except Exception as e:
                    session.add_message("error", {
                        "action": "get_unread_ids",
                        "error": str(e)
                    })
                    return {"success": False, "error": str(e)}
                
                all_ids = [chat["id"] for chat in all_chats_result["chats"]]
                
                # Verify unread IDs exist in all chats
                missing_ids = [uid for uid in unread_ids if uid not in all_ids]
                
         
                return {
                    "success": True,
                    "all_chat_ids": all_ids,
                    "unread_chat_ids": unread_ids,
                    "missing_ids": missing_ids,
                    "consistent": len(missing_ids) == 0
                }
                
            except Exception as e:
                session.add_message("error", {
                    "action": "verify_chat_ids",
                    "error": str(e)
                })
                return {"success": False, "error": str(e)}




        @staticmethod
        async def open_unread_chat(session: "AutomationSession", click_delay: float = 1.0, verify_ids: bool = True) -> dict:
                """
                Find the first unread chat using Selenium, click it to open, and log its chat ID.
                Optionally verifies chat ID consistency before opening.
                
                Args:
                    session: AutomationSession instance
                    click_delay: Delay in seconds before returning (default: 1.0)
                    verify_ids: Whether to verify chat IDs before opening (default: True)
                
                Returns:
                    dict with success status and opened chat ID
                """
                try:
                    if not session.driver:
                        session.add_message("error", {"message": "Driver not initialized"})
                        return {"success": False, "error": "Driver not initialized"}
                    
                    # Verify chat IDs consistency if requested
                    if verify_ids:
                        verification = await AutomationActions.verify_chat_ids(session)
                        if not verification["success"]:
                            session.add_message("warning", {"message": "Chat ID verification failed, proceeding anyway"})
                        elif not verification["consistent"]:
                            session.add_message("warning", {
                                "message": "Some chat IDs are inconsistent",
                                "missing_ids": verification["missing_ids"]
                            })
                    
                    # Wait for chat list to be present
                    try:
                        chat_list = WebDriverWait(session.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Chat list"]'))
                        )
                    except TimeoutException:
                        session.add_message("error", {"message": "Chat list not found"})
                        return {"success": False, "error": "Chat list not found - user may not be logged in"}
                    
                    # Get all chat rows
                    try:
                        chat_rows = chat_list.find_elements(By.CSS_SELECTOR, '[role="row"]')
                    except NoSuchElementException:
                        session.add_message("error", {"message": "No chat rows found"})
                        return {"success": False, "error": "No chat rows found"}
                    
                    if len(chat_rows) == 0:
                        session.add_message("status", {"message": "Chat list is empty"})
                        return {"success": False, "error": "No chats available"}
                    
                    # Find the first unread chat using Selenium
                    for index, row in enumerate(chat_rows):
                        try:
                            # Check for unread message counter
                            unread_count_element = None
                            try:
                                # Look for elements with aria-label ending in "unread message" or "unread messages"
                                unread_elements = row.find_elements(By.CSS_SELECTOR, '[aria-label*="unread message"]')
                                for elem in unread_elements:
                                    aria_label = elem.get_attribute('aria-label')
                                    if aria_label and ('unread message' in aria_label or 'unread messages' in aria_label):
                                        unread_count_element = elem
                                        break
                            except NoSuchElementException:
                                continue
                            
                            if not unread_count_element:
                                continue
                            
                            # This chat is unread - extract details
                            
                            # 1. Get the Title (Contact Name/Number)
                            title = "Title Not Found"
                            try:
                                title_element = row.find_element(By.CSS_SELECTOR, '[title]')
                                title = title_element.get_attribute('title').strip()
                            except NoSuchElementException:
                                pass
                            
                            # 2. Get the Unread Count
                            unread_count = 1
                            try:
                                aria_label = unread_count_element.get_attribute('aria-label')
                                if aria_label:
                                    import re
                                    match = re.search(r'\d+', aria_label)
                                    if match:
                                        unread_count = int(match.group(0))
                            except:
                                pass
                            
                            # 3. Get the Recent Message/Description
                            description = "Description Not Found"
                            try:
                                message_span = row.find_element(By.CSS_SELECTOR, 'div[role="gridcell"]:nth-child(2) + div span[dir="ltr"]')
                                description = message_span.text.strip()
                            except NoSuchElementException:
                                pass
                            
                            # 4. Get Chat ID from href
                            chat_id = None
                            try:
                                link_element = row.find_element(By.CSS_SELECTOR, 'a[href*="web.whatsapp.com"]')
                                href = link_element.get_attribute('href')
                                
                                # Extract chat ID
                                import re
                                match = re.search(r'[0-9]+@[cgs]\.us', href)
                                if match:
                                    chat_id = match.group(0)
                            except NoSuchElementException:
                                pass
                            
                            # Fallback for chat ID
                            if not chat_id:
                                try:
                                    chat_id = row.get_attribute('data-id')
                                except:
                                    pass
                            
                            if not chat_id:
                                chat_id = f"chat_{index}"
                            
                            # Click the chat using Selenium
                            try:
                                WebDriverWait(session.driver, 5).until(
                                    EC.element_to_be_clickable(row)
                                )
                                row.click()
                                
                             
                                
                                # Wait before returning
                                await asyncio.sleep(click_delay)
                                
                                return {
                                    "success": True,
                                    "opened_chat": {
                                        "id": chat_id
                                    }
                                }
                                
                            except Exception as e:
                                session.add_message("error", {
                                    "action": "click_unread_chat",
                                    "chat_id": chat_id,
                                    "chat_title": title,
                                    "error": str(e)
                                })
                                continue
                            
                        except Exception as e:
                            session.add_message("error", {
                                "action": "parse_unread_chat",
                                "index": index,
                                "error": str(e)
                            })
                            continue
                    
                    # No unread chats found
                    session.add_message("status", {
                        "message": "No unread chats found"
                    })
                    return {"success": False, "error": "No unread chats found"}
                    
                except Exception as e:
                    return {"success": False, "error": str(e)}



        @staticmethod
        async def extract_chat_history(session: "AutomationSession", limit: int = 50) -> dict:
            """
            Extract chat history from the currently open WhatsApp chat using Selenium.
            Returns grouped messages with sender, message text, and timestamp.
            
            Args:
                session: AutomationSession object with driver instance
                limit: Maximum number of recent messages to extract (from bottom). If None, extracts all messages.
            
            Returns:
                dict with success status, grouped chat history, and message counts
            """
            try:
                if not session.driver:
                    session.add_message("error", {"message": "Driver not initialized"})
                    return {"success": False, "error": "Driver not initialized"}
                
                # Array to hold the final output: an array of message groups
                grouped_chat_history = []
                
                # Counters for different message types
                total_messages = 0
                my_messages = 0
                sender_messages = 0
                
                # 1. Target all elements that bundle messages together (the groups)
                try:
                    group_containers = session.driver.find_elements(By.CSS_SELECTOR, '.x1n2onr6')
                except NoSuchElementException:
                    group_containers = []
                
                if len(group_containers) == 0:
                    session.add_message("log", {
                        "message": "Could not find any message groups (.x1n2onr6). Checking for system messages..."
                    })
                    
                    # Fallback for system messages, often outside main groups
                    try:
                        system_messages = session.driver.find_elements(By.CSS_SELECTOR, 'div[role="button"] span._ao3e')
                        if len(system_messages) > 0:
                            session.add_message("log", {"message": "Found only system messages"})
                            return {
                                "success": True,
                                "chat_history": [[{
                                    "sender": "System",
                                    "message": system_messages[0].text.strip(),
                                    "time": "N/A"
                                }]],
                                "total_groups": 1,
                                "total_messages": 1,
                                "my_messages": 0,
                                "sender_messages": 0
                            }
                    except NoSuchElementException:
                        pass
                    
                    session.add_message("warning", {
                        "message": "No chat messages found. Ensure a chat is open and loaded."
                    })
                    return {
                        "success": True,
                        "chat_history": [],
                        "total_groups": 0,
                        "total_messages": 0,
                        "my_messages": 0,
                        "sender_messages": 0
                    }
                
                # Collect all messages first (to apply limit from bottom)
                all_messages_flat = []
                
                # Iterate through each message group container
                for group_index, group_container in enumerate(group_containers):
                    group_messages = []
                    
                    try:
                        # 2. Find individual message bubbles (incoming or outgoing) within this group
                        message_containers = group_container.find_elements(By.CSS_SELECTOR, '.message-in, .message-out')
                        
                        for msg_index, container in enumerate(message_containers):
                            try:
                                sender = "Unknown"
                                timestamp = "Time Not Found"
                                is_my_message = False
                                
                                # Determine the sender based on the message bubble class
                                class_list = container.get_attribute('class')
                                if 'message-out' in class_list:
                                    sender = "My (Outgoing)"
                                    is_my_message = True
                                elif 'message-in' in class_list:
                                    sender = "His (Incoming)"
                                
                                # 3. Extract the timestamp
                                try:
                                    time_element = container.find_element(By.CSS_SELECTOR, 'span.x1c4vz4f.x2lah0s')
                                    timestamp = time_element.text.strip() or "Time Not Found"
                                except NoSuchElementException:
                                    pass
                                
                                # 4. Extract the message text
                                message_text = "Media or Empty Message"
                                try:
                                    text_element = container.find_element(By.CSS_SELECTOR, 'span.selectable-text')
                                    message_text = text_element.text.strip() or "Media or Empty Message"
                                except NoSuchElementException:
                                    pass
                                
                                # 5. Fallback/Group Chat Sender Name (using data-pre-plain-text on an ancestor)
                                try:
                                    # Find ancestor with data-pre-plain-text attribute
                                    pre_text_ancestor = session.driver.execute_script("""
                                        var element = arguments[0];
                                        while (element && !element.getAttribute('data-pre-plain-text')) {
                                            element = element.parentElement;
                                        }
                                        return element;
                                    """, container)
                                    
                                    if pre_text_ancestor:
                                        pre_text_content = pre_text_ancestor.get_attribute('data-pre-plain-text')
                                        
                                        if pre_text_content:
                                            import re
                                            
                                            # Try to parse out sender name from data-pre-plain-text
                                            name_match = re.search(r'\[.*?\]\s*([^:]+):', pre_text_content)
                                            if name_match and name_match.group(1) and sender == "His (Incoming)":
                                                # Use just the extracted name for a cleaner context
                                                sender = name_match.group(1).strip()
                                            
                                            # Try to extract timestamp from pre-plain-text if not found otherwise
                                            if timestamp == "Time Not Found":
                                                time_match = re.search(r'\[(\d{1,2}:\d{2}\s*(?:AM|PM)?)\]', pre_text_content)
                                                if time_match:
                                                    timestamp = time_match.group(1)
                                except:
                                    pass
                                
                                # Clean up the sender string for better context
                                if sender == "My (Outgoing)":
                                    sender = "Me"
                                elif "(Incoming)" in sender:
                                    sender = sender.replace(" (Incoming)", "").strip()
                                elif sender == "His (Incoming)":
                                    sender = "Other Contact"
                                
                                message_obj = {
                                    "sender": sender,
                                    "message": message_text,
                                    "time": timestamp
                                }
                                
                                group_messages.append(message_obj)
                                all_messages_flat.append(message_obj)
                                
                            except Exception as e:
                                session.add_message("error", {
                                    "action": "parse_message",
                                    "group_index": group_index,
                                    "message_index": msg_index,
                                    "error": str(e)
                                })
                                continue
                        
                        # Add the group of messages to the final history array only if it contains messages
                        if len(group_messages) > 0:
                            grouped_chat_history.append(group_messages)
                            
                    except Exception as e:
                        continue
                
                # Apply limit from the bottom (most recent messages)
                if limit is not None and limit > 0:
                    all_messages_flat = all_messages_flat[-limit:]
                    
                    # Rebuild grouped_chat_history with only limited messages
                    limited_grouped_history = []
                    for group in grouped_chat_history:
                        limited_group = [msg for msg in group if msg in all_messages_flat]
                        if limited_group:
                            limited_grouped_history.append(limited_group)
                    
                    grouped_chat_history = limited_grouped_history
                    total_messages = len(all_messages_flat)
                    my_messages = sum(1 for msg in all_messages_flat if msg["sender"] == "Me")
                    sender_messages = len(all_messages_flat) - my_messages
                else:
                    total_messages = len(all_messages_flat)
                    my_messages = sum(1 for msg in all_messages_flat if msg["sender"] == "Me")
                    sender_messages = len(all_messages_flat) - my_messages
                
                session.add_message("log", {
                    "message": f"Extracted chat history: {len(grouped_chat_history)} groups, {total_messages} total messages ({my_messages} from me, {sender_messages} from sender)" + (f" (Limited to last {limit} messages)" if limit else ""),
                    "total_groups": len(grouped_chat_history),
                    "total_messages": total_messages,
                    "my_messages": my_messages,
                    "sender_messages": sender_messages
                })
                
                return {
                    "success": True,
                    "chat_history": grouped_chat_history,
                    "total_groups": len(grouped_chat_history),
                    "total_messages": total_messages,
                    "my_messages": my_messages,
                    "sender_messages": sender_messages
                }
                
            except Exception as e:
                session.add_message("error", {
                    "action": "extract_chat_history",
                    "error": str(e)
                })
                return {"success": False, "error": str(e)}


        @staticmethod
        def format_chat_history_for_ai(grouped_history: List[List[dict]]) -> str:
            """
            Format grouped chat history into a readable text format for AI processing.
            
            Args:
                grouped_history: List of message groups (from extract_chat_history)
            
            Returns:
                Formatted string with conversation history
            """
            if not grouped_history or len(grouped_history) == 0:
                return "Chat history is empty."
            
            formatted_text = "--- BEGIN CONVERSATION HISTORY ---\n\n"
            
            for group_index, message_group in enumerate(grouped_history):
                # Iterate over messages within a group
                for message_index, message in enumerate(message_group):
                    time = f"[{message['time']}]" if message['time'] != 'Time Not Found' else ''
                    
                    # Format: Sender [Time]: Message
                    formatted_text += f"{message['sender']} {time}: {message['message']}\n"
                
                # Add a blank line to separate groups
                # We only add a separator if it's not the last group
                if group_index < len(grouped_history) - 1:
                    formatted_text += "\n"
            
            formatted_text += "\n--- END CONVERSATION HISTORY ---"
            
            return formatted_text

        @staticmethod
        async def extract_and_format_chat_history(session: "AutomationSession") -> dict:
            """
            Extract chat history and return both raw and AI-formatted versions.
            Convenience method that combines extract_chat_history and format_chat_history_for_ai.
            
            Returns:
                dict with success status, raw chat history, and formatted text
            """
            try:
                # Extract chat history
                result = await AutomationActions.extract_chat_history(session)
                
                if not result["success"]:
                    return result
                
                # Format for AI
                formatted_text = AutomationActions.format_chat_history_for_ai(result["chat_history"])
                
                session.add_message("log", {
                    "message": "Chat history extracted and formatted for AI",
                    "formatted_length": len(formatted_text)
                })
                
                return {
                    "success": True,
                    "formatted_text": formatted_text,
                    "total_groups": result["total_groups"],
                    "total_messages": result["total_messages"],
                    "my_messages": result["my_messages"],
                    "sender_messages": result["sender_messages"]

                }
                
            except Exception as e:
                session.add_message("error", {
                    "action": "extract_and_format_chat_history",
                    "error": str(e)
                })
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
