from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, List
from session import AutomationSession
import asyncio

class AutomationActions:
    """Handles automation actions"""
    
    @staticmethod
    async def initialize(session: AutomationSession, url: str = "https://web.whatsapp.com/", headless: bool = False) -> dict:
        """Initialize browser and navigate to URL"""
        try:
            if not session.driver:
                session.create_driver(headless=headless)
            
            session.driver.get(url)
            
            # Wait for page load
            WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            
            session.add_message("log", {
                "action": "navigate",
                "url": url,
                "profile": session.profile_name
            })
            
            return {
                "success": True,
                "title": session.driver.title,
                "url": session.driver.current_url
            }
        except Exception as e:
            session.add_message("error", {"action": "navigate", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_qr_code(session: AutomationSession) -> dict:
        """Extract QR code as base64"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            canvas = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            
            base64_data = session.driver.execute_script(
                "return arguments[0].toDataURL('image/png');",
                canvas
            )
            
            session.add_message("log", {"action": "qr_code_extracted"})
            return {"success": True, "qr_code": base64_data}
        except Exception as e:
            session.add_message("error", {"action": "get_qr_code", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_message(session: AutomationSession, contact: str, message: str) -> dict:
        """Send message to contact"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            # TODO: Add your scraping logic here
            # Steps:
            # 1. Search for contact
            # 2. Click contact
            # 3. Type message
            # 4. Send message
            
            session.add_message("log", {
                "action": "send_message",
                "contact": contact,
                "message": message
            })
            
            return {
                "success": True,
                "message": f"Message sent to {contact}",
                "contact": contact
            }
        except Exception as e:
            session.add_message("error", {"action": "send_message", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def click_element(session: AutomationSession, selector: str, selector_type: str = "css") -> dict:
        """Click an element by selector"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            by_type = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = WebDriverWait(session.driver, 10).until(
                EC.element_to_be_clickable((by_type, selector))
            )
            element.click()
            
            session.add_message("log", {
                "action": "click_element",
                "selector": selector,
                "type": selector_type
            })
            
            await asyncio.sleep(1)
            return {"success": True, "message": f"Clicked element: {selector}"}
        except Exception as e:
            session.add_message("error", {"action": "click_element", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def type_text(session: AutomationSession, selector: str, text: str, selector_type: str = "css") -> dict:
        """Type text into an element"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            by_type = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((by_type, selector))
            )
            element.clear()
            element.send_keys(text)
            
            session.add_message("log", {
                "action": "type_text",
                "selector": selector,
                "text": text[:50] + "..." if len(text) > 50 else text
            })
            
            return {"success": True, "message": f"Typed text into element"}
        except Exception as e:
            session.add_message("error", {"action": "type_text", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def extract_text(session: AutomationSession, selector: str, selector_type: str = "css") -> dict:
        """Extract text from element"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            by_type = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            element = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((by_type, selector))
            )
            text = element.text
            
            session.add_message("log", {
                "action": "extract_text",
                "selector": selector
            })
            
            return {"success": True, "text": text}
        except Exception as e:
            session.add_message("error", {"action": "extract_text", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def extract_multiple(session: AutomationSession, selector: str, selector_type: str = "css") -> dict:
        """Extract text from multiple elements"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            by_type = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            elements = session.driver.find_elements(by_type, selector)
            texts = [el.text for el in elements]
            
            session.add_message("log", {
                "action": "extract_multiple",
                "selector": selector,
                "count": len(texts)
            })
            
            return {"success": True, "items": texts, "count": len(texts)}
        except Exception as e:
            session.add_message("error", {"action": "extract_multiple", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def wait_element(session: AutomationSession, selector: str, timeout: int = 10, selector_type: str = "css") -> dict:
        """Wait for element to be present"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            by_type = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            WebDriverWait(session.driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            
            session.add_message("log", {
                "action": "wait_element",
                "selector": selector
            })
            
            return {"success": True, "message": f"Element found: {selector}"}
        except Exception as e:
            session.add_message("error", {"action": "wait_element", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def scroll(session: AutomationSession, direction: str = "down", amount: int = 3) -> dict:
        """Scroll page"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            if direction.lower() == "down":
                session.driver.execute_script(f"window.scrollBy(0, {amount * 500});")
            elif direction.lower() == "up":
                session.driver.execute_script(f"window.scrollBy(0, {-amount * 500});")
            
            session.add_message("log", {
                "action": "scroll",
                "direction": direction,
                "amount": amount
            })
            
            await asyncio.sleep(1)
            return {"success": True, "message": f"Scrolled {direction}"}
        except Exception as e:
            session.add_message("error", {"action": "scroll", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_page_source(session: AutomationSession) -> dict:
        """Get page HTML"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            source = session.driver.page_source
            
            session.add_message("log", {"action": "get_page_source"})
            
            return {"success": True, "page_source": source}
        except Exception as e:
            session.add_message("error", {"action": "get_page_source", "error": str(e)})
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def execute_script(session: AutomationSession, script: str) -> dict:
        """Execute custom JavaScript"""
        try:
            if not session.driver:
                return {"success": False, "error": "Driver not initialized"}
            
            result = session.driver.execute_script(script)
            
            session.add_message("log", {"action": "execute_script"})
            
            return {"success": True, "result": result}
        except Exception as e:
            session.add_message("error", {"action": "execute_script", "error": str(e)})
            return {"success": False, "error": str(e)}







# Standalone testing
if __name__ == "__main__":
    import asyncio
    from session import AutomationSession
    
    async def test_automation():
        """Test automation actions independently"""
        print("🧪 Testing Automation Actions\n")
        
        # Create a test session
        session = AutomationSession("test-session-001", "testing")
        session.config['headless'] = False  # GUI mode
        
        print("1️⃣ Creating driver...")
        session.create_driver(headless=False)
        print("✅ Driver created (Chrome window should be visible)\n")
        
        # Test navigate
        print("2️⃣ Testing navigation...")
        result = await AutomationActions.Initialize(session, "https://web.whatsapp.com/")
        print(f"✅ Navigate: {result}\n")
        
        # Keep browser open
        print("\n⏸️  Browser will stay open. Press Enter to close...")
        input()
        
        # Cleanup
        print("🧹 Cleaning up...")
        session.cleanup()
        print("✅ Done!")
    
    # Run the test
    asyncio.run(test_automation())