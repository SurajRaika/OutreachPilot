import requests
import time

BASE_URL = "http://localhost:8000/api"


# -------------------------------
# 🔹 Session Creation & Management
# -------------------------------
def create_session(session_id: str = None):
    """Create a new automation session or resume an existing one."""
    payload = {
        "session_type": "whatsapp",
        "config": {},
        "headless": False
    }
    if session_id:
        payload["session_id"] = session_id
        print(f"Attempting to **RESUME** session with ID: {session_id}")
    else:
        print("Attempting to **CREATE** new session.")

    response = requests.post(f"{BASE_URL}/sessions/create", json=payload)
    print("Create/Resume response:", response.json())
    return response.json()


def list_saved_sessions():
    """List saved sessions from disk (/sessions_list)"""
    response = requests.get(f"{BASE_URL}/sessions_list")
    print("Saved sessions (disk) response:", response.json())
    return response.json()


def list_active_sessions():
    """List currently active sessions in memory (/sessions/list)"""
    response = requests.get(f"{BASE_URL}/sessions/list")
    print("Active sessions (memory) response:", response.json())
    return response.json()


def get_session_from_saved():
    """Get the first saved session ID"""
    sessions = list_saved_sessions()
    if "sessions" in sessions and sessions["sessions"]:
        return sessions["sessions"][0]["session_id"]
    print("⚠️ No saved sessions found.")
    return None


def get_session_from_active():
    """Get the first active session ID"""
    sessions = list_active_sessions()
    if "sessions" in sessions and sessions["sessions"]:
        # Depends on what session_manager.list_sessions() returns — assume list of dicts
        sess = sessions["sessions"][0]
        if isinstance(sess, dict) and "session_id" in sess:
            return sess["session_id"]
        return sess  # fallback if it's just a string
    print("⚠️ No active sessions found.")
    return None
# -------------------------------
# 🔹 Session Actions
# -------------------------------

def init_driver(session_id):
    """Initialize browser driver for a session"""
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/init-driver")
    print("Init driver response:", response.json())
    return response.json()


def navigate_to_whatsapp(session_id):
    """Navigate to WhatsApp Web (init handled separately)"""
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/actions/navigate",
        params={"url": "https://web.whatsapp.com"}
    )
    print("Navigate response:", response.json())
    return response.json()


def get_qr_code(session_id):
    """Fetch WhatsApp QR code (base64 data)"""
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/whatsapp/qr-code")
    print("QR Code response:", response.json())
    return response.json()


def get_session_info(session_id):
    """Get info about a session"""
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    print("Session info:", response.json())
    return response.json()


def stop_session(session_id):
    """Stop the current session"""
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/stop")
    print("Stop response:", response.json())
    return response.json()


def delete_session(session_id):
    """Delete a specific session"""
    response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
    print("Delete response:", response.json())
    return response.json()
