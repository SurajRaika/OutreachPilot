import requests
import time
import uuid

BASE_URL = "http://localhost:8000/api"
resume_result = create_session(session_id=saved_session_id)
if not resume_result['success']:
    print("❌ Failed to resume session.")
    return

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
    """Get the first saved session ID that is not currently active"""
    sessions = list_saved_sessions()
    if "sessions" in sessions and sessions["sessions"]:
        # Find one that is not active to test resumption cleanly
        for sess in sessions["sessions"]:
            if not sess.get("is_active", False):
                 print(f"✅ Found saved (inactive) session ID: {sess['session_id']}")
                 return sess["session_id"]

        # If all are active, just take the first one
        print(f"⚠️ All saved sessions are active. Using first ID: {sessions['sessions'][0]['session_id']}")
        return sessions["sessions"][0]["session_id"]

    print("⚠️ No saved sessions found.")
    return None


def get_session_from_active():
    """Get the first active session ID"""
    sessions = list_active_sessions()
    if "sessions" in sessions and sessions["sessions"]:
        # Depends on what session_manager.list_sessions() returns — assume list of dicts
        sess = sessions["sessions"][0]
        return sess["session_id"]
    print("⚠️ No active sessions found.")
    return None


# -------------------------------
# 🔹 Session Actions
# -------------------------------

def init_driver(session_id):
    """Initialize browser driver for a session (must be called after create/resume)"""
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
    """Stop the current session (closes browser, profile stays on disk)"""
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/stop")
    print("Stop response:", response.json())
    return response.json()


def delete_session(session_id):
    """Delete a specific session (removes from memory and closes driver)"""
    response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
    print("Delete response:", response.json())
    return response.json()


# -------------------------------
# 🧪 Test Scenarios
# -------------------------------

def test_full_cycle():
    """Test a full create -> navigate -> stop cycle"""
    print("--- Test Full Session Cycle (Create & Save) ---")
    
    # 1. Create a new session
    create_result = create_session()
    session_id = create_result['data']['session_id']
    if not session_id:
        print("❌ Failed to create session.")
        return
    
    # 2. Initialize driver (a new Chrome window opens)
    init_driver(session_id)
    
    # 3. Navigate to WhatsApp
    navigate_to_whatsapp(session_id)
    # At this point, you would scan the QR code to save login data to disk
    print(f"\n💡 Session {session_id} is active. If a QR code is shown, scan it now to save your login state to disk.")
    time.sleep(3) # Wait for a moment
    
    # 4. Stop the session (closes browser, profile remains on disk)
    print("\n4. Stopping session (profile saved)...")
    stop_session(session_id) 
    
    # 5. List sessions to confirm it's no longer active but should be saved
    print("\n5. Listing active sessions after stopping:")
    list_active_sessions() 

def test_resume_cycle():
    """Test resuming a session that was previously stopped (and thus saved to disk)"""
    print("\n--- Test Session Resume Cycle ---")

    # A. Look for a session saved on disk that is currently inactive
    saved_session_id = get_session_from_saved()

    if not saved_session_id:
        print("❌ Cannot proceed with resume test: No saved sessions found or all are active.")
        return
    
    # B. Resume the session (loads object into memory using the old ID)
    resume_result = create_session(session_id=saved_session_id)
    if not resume_result['success']:
        print("❌ Failed to resume session.")
        return

    # C. Initialize the driver (this loads the persistent profile from disk)
    print("\nC. Initializing driver on resumed session (opens Chrome window with old state)...")
    init_driver(saved_session_id)
    
    # D. Navigate again - if the login was saved, it should immediately be logged in.
    print("D. Navigating to WhatsApp. Should load saved session state.")
    navigate_to_whatsapp(saved_session_id)

    print("\n✅ Resume Test Complete. Check the browser window to see if the session was loaded correctly.")
    time.sleep(5)
    
    # E. Stop and delete the resumed session
    print("\nE. Stopping and deleting resumed session.")
    stop_session(saved_session_id)
    delete_session(saved_session_id)


def main():
    print("Starting example usage. Please ensure the FastAPI server is running.")
        
    # List existing profiles on disk
    

    
    # Attempt to resume the session created in the full cycle
    test_resume_cycle()

    print("\nCleanup check:")
    list_active_sessions()


if __name__ == "__main__":
    main()