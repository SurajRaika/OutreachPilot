from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional
import os

class DriverManager:
    """Manages Chrome WebDriver instances"""

    @staticmethod
    def create_driver(session_id: str, headless: bool = False) -> webdriver.Chrome:
        """Create a new Chrome driver with persistent session support"""
        chrome_options = webdriver.ChromeOptions()

        # Optional headless mode
        if headless:
            chrome_options.add_argument("--headless=new")  # use new headless mode

        # Essential stability flags for Linux
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # ✅ Persistent session directory
        session_dir = f"/home/suraj/chrome_selenium/session_{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={session_dir}")

        # Optional: distinct profile name if you want multiple profiles inside same dir
        chrome_options.add_argument("--profile-directory=Default")

        # Performance tweaks (disable images, notifications)
        prefs = {
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Start Chrome
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        driver.set_page_load_timeout(30)
        return driver

    @staticmethod
    def safe_quit(driver: Optional[webdriver.Chrome]):
        """Safely quit a driver instance"""
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {e}")
