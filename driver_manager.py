from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional
import os

class DriverManager:
    """Manages Chrome WebDriver instances with profile support"""
    
    BASE_PATH = "/home/suraj/chrome_selenium"
    
    @staticmethod
    def create_driver(session_id: str, profile_name: str, headless: bool = False) -> webdriver.Chrome:
        """Create Chrome driver with profile management"""
        chrome_options = webdriver.ChromeOptions()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Create profile-based session directory using encoded session_id
        # Extract base_uuid from encoded_id for directory naming
        base_uuid = session_id.split("||")[0] if "||" in session_id else session_id
        session_dir = os.path.join(DriverManager.BASE_PATH, f"session_{base_uuid}_{profile_name}")
        os.makedirs(session_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={session_dir}")
        chrome_options.add_argument("--profile-directory=Default")
        
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        driver.set_page_load_timeout(30)
        return driver
    
    @staticmethod
    def safe_quit(driver: Optional[webdriver.Chrome]):
        """Safely quit driver"""
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {e}")