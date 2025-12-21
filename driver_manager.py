from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional
import os
import platform
import shutil
from utils.global_utils import get_base_path   # <--- imported
import psutil

class DriverManager:

    @staticmethod
    def find_chrome_binary() -> str:
        """Locate chrome/chromium binary on Windows & Linux"""
        possible_paths = []

        if platform.system() == "Windows":
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                shutil.which("chrome"),
                shutil.which("chrome.exe"),
                shutil.which("google-chrome")
            ]
        else:  # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/snap/bin/chromium",
                shutil.which("google-chrome"),
                shutil.which("chromium"),
                shutil.which("chromium-browser")
            ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        raise FileNotFoundError("Chrome browser binary not found on system!")

    @staticmethod
    def create_driver(session_id: str, profile_name: str, headless: bool = False) -> webdriver.Chrome:
        chrome_options = webdriver.ChromeOptions()

        # Headless if enabled
        # if headless:
        chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-session-crashed-bubble")

        prefs = {
            "profile.exit_type": "Normal",
            "profile.session_info": {"last_exit_type": "Normal"},
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        # Add binary path explicitly
        chrome_options.binary_location = DriverManager.find_chrome_binary()

        # Profile management
        base_path = get_base_path()
        session_dir = os.path.join(base_path, f"session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        chrome_options.add_argument(f"--user-data-dir={session_dir}")
        chrome_options.add_argument("--profile-directory=Default")

        # Disable notifications
     

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.set_page_load_timeout(30)
        return driver

    @staticmethod
    def safe_quit(driver):
        if driver:
            try:
                driver.quit()
            finally:
                # Kill ALL orphan Chrome processes tied to Selenium
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'chrome' in proc.info['name'].lower():
                            proc.kill()
                    except Exception:
                        pass
