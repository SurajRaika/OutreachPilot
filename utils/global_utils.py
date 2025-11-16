import os
import platform

def get_base_path() -> str:
    """Return OS-specific base storage directory for browser profiles"""
    system = platform.system()

    if system == "Windows":
        return os.path.join(os.environ["USERPROFILE"], "chrome_selenium")
    elif system == "Linux":
        return os.path.join(os.path.expanduser("~"), "chrome_selenium")
    else:
        raise Exception(f"Unsupported OS: {system}")
