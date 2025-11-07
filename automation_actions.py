from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from typing import Optional, List, Dict

from session import AutomationSession
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class AutomationActions:
    """Handles automation actions for sessions"""
    
    @staticmethod
    async def Initialize(session: AutomationSession, url: str="https://web.whatsapp.com/", headless: bool = False) -> dict:
        """Navigate to a URL"""
        try:
            if not session.driver:
                session.create_driver(headless=headless)
            
            session.driver.get(url)

            # Use a generic CSS selector 'canvas' or a more specific one if available
            canvas_selector = "canvas"
            canvas_element = WebDriverWait(session.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, canvas_selector))
            )
            print("Canvas element found.")

            # 2. Execute JavaScript to get the base64 Data URL
            # The JavaScript returns the result of the canvas.toDataURL() call.
            # 'arguments[0]' refers to the canvas_element passed to the script.
            base64_data_url = session.driver.execute_script(
                "return arguments[0].toDataURL('image/png');", 
                canvas_element
            )

            # 3. Print the resulting Base64 Data URL
            print(f"\nBase64 Data URL (first 100 chars): {base64_data_url[:100]}...")






            session.add_message("log", {
                "action": "navigate",
                "url": url,
                "current_url": session.driver.current_url
            })
            
            return {
                "success": True,
                "base64_data_url": base64_data_url,
                "title": session.driver.title
            }
        except Exception as e:
            session.add_message("error", {
                "action": "navigate",
                "error": str(e)
            })








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