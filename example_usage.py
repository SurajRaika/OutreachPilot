"""
test_cli.py - Manual testing script for WhatsApp automation sessions
Run this script to test session operations without FastAPI
"""
import asyncio
import json
from manager import session_manager, SessionManager
from models import AgentType

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

async def test_create_session():
    """Test creating new sessions"""
    print_header("TEST 1: CREATE NEW SESSIONS")
    
    profiles = ["Account_1", "Business_Account", "Support_Team"]
    session_ids = []
    
    for profile in profiles:
        session_id = session_manager.create_session(profile_name=profile)
        session_ids.append(session_id)
        print_success(f"Created session: {session_id}")
        print(f"  Profile: {profile}\n")
    
    return session_ids

def test_list_active_sessions(session_ids):
    """Test listing active sessions"""
    print_header("TEST 2: LIST ACTIVE SESSIONS")
    
    sessions = session_manager.list_sessions()
    print_info(f"Total active sessions: {len(sessions)}\n")
    
    for s in sessions:
        print(f"Session ID: {s['session_id']}")
        print(f"Profile Name: {s['profile_name']}")
        print(f"Status: {s['status']}")
        print(f"Has Driver: {s['has_driver']}")
        print()

def test_list_saved_profiles():
    """Test listing saved profiles from disk"""
    print_header("TEST 3: LIST SAVED PROFILES (DISK)")
    
    profiles = session_manager.list_saved_profiles()
    
    if not profiles:
        print_info("No saved profiles on disk yet\n")
        return
    
    print_info(f"Total saved profiles: {len(profiles)}\n")
    
    for p in profiles:
        print(f"Session ID: {p['encoded_session_id']}")
        print(f"Profile Name: {p['profile_name']}")
        print(f"Is Active: {p['is_active']}")
        print()

def test_stop_session(session_id):
    """Test stopping a session"""
    print_header("TEST 4: STOP SESSION")
    
    print_info(f"Stopping session: {session_id}\n")
    
    if session_manager.stop_session(session_id):
        print_success(f"Session stopped: {session_id}")
        print_info("Profile saved to disk\n")
    else:
        print_error(f"Failed to stop session: {session_id}\n")

def test_pause_session(session_id):
    """Test pausing a session"""
    print_header("TEST 5: PAUSE SESSION")
    
    print_info(f"Pausing session: {session_id}\n")
    
    if session_manager.pause_session(session_id):
        print_success(f"Session paused: {session_id}")
        print_info("Driver closed, session in memory\n")
    else:
        print_error(f"Failed to pause session: {session_id}\n")

def test_resume_session(session_id):
    """Test resuming a paused session"""
    print_header("TEST 6: RESUME PAUSED SESSION")
    
    print_info(f"Resuming session: {session_id}\n")
    
    if session_manager.resume_session(session_id):
        print_success(f"Session resumed: {session_id}\n")
    else:
        print_error(f"Failed to resume session: {session_id}\n")

def test_resume_from_disk(encoded_session_id):
    """Test resuming a saved session from disk"""
    print_header("TEST 7: RESUME FROM DISK")
    
    base_uuid, profile_name = SessionManager.decode_session_id(encoded_session_id)
    print_info(f"Resuming from disk:")
    print(f"  Session ID: {encoded_session_id}")
    print(f"  Profile Name: {profile_name}\n")
    
    session_id = session_manager.create_session(
        profile_name=profile_name,
        session_id=encoded_session_id
    )
    
    print_success(f"Session resumed from disk: {session_id}\n")
    return session_id

def test_delete_session(session_id):
    """Test deleting a session"""
    print_header("TEST 8: DELETE SESSION")
    
    print_info(f"Deleting session: {session_id}\n")
    
    if session_manager.delete_session(session_id):
        print_success(f"Session deleted: {session_id}\n")
    else:
        print_error(f"Failed to delete session: {session_id}\n")

def test_get_session_info(session_id):
    """Test getting session info"""
    print_header("TEST 9: GET SESSION INFO")
    
    session = session_manager.get_session(session_id)
    if not session:
        print_error(f"Session not found: {session_id}\n")
        return
    
    info = session.get_info()
    print(json.dumps(info, indent=2))
    print()

async def test_agents(session_id):
    """Test agent enable/disable"""
    print_header("TEST 10: TEST AGENTS")
    
    session = session_manager.get_session(session_id)
    if not session:
        print_error(f"Session not found: {session_id}\n")
        return
    
    # Enable autoreply agent
    print_info("Enabling autoreply agent...")
    await session.enable_agent(AgentType.AUTOREPLY)
    print_success("Autoreply agent enabled\n")
    
    # Check status
    statuses = session.get_agent_statuses()
    print(f"Agent statuses: {json.dumps(statuses, indent=2)}\n")
    
    # Pause autoreply agent
    print_info("Pausing autoreply agent...")
    await session.pause_agent(AgentType.AUTOREPLY)
    print_success("Autoreply agent paused\n")
    
    # Resume autoreply agent
    print_info("Resuming autoreply agent...")
    await session.resume_agent(AgentType.AUTOREPLY)
    print_success("Autoreply agent resumed\n")
    
    # Disable autoreply agent
    print_info("Disabling autoreply agent...")
    await session.disable_agent(AgentType.AUTOREPLY)
    print_success("Autoreply agent disabled\n")

async def main():
    """Main test runner"""
    print(f"\n{Colors.BLUE}")
    print("  ╔══════════════════════════════════════════════════════════╗")
    print("  ║     WhatsApp Automation - Manual Testing Suite          ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    try:
        # Test 1: Create sessions
        session_ids = await test_create_session()
        
        # Test 2: List active
        test_list_active_sessions(session_ids)
        
        # Test 3: List saved (will be empty on first run)
        test_list_saved_profiles()
        
        # Test 4: Get session info
        test_get_session_info(session_ids[0])
        
        # Test 5: Pause session
        test_pause_session(session_ids[1])
        
        # Test 6: Resume paused session
        test_resume_session(session_ids[1])
        
        # Test 7: Stop session (saves to disk)
        test_stop_session(session_ids[0])
        
        # Test 8: List saved profiles again (should show stopped session)
        test_list_saved_profiles()
        
        # Test 9: Resume from disk
        saved_profiles = session_manager.list_saved_profiles()
        if saved_profiles:
            resumed_id = await test_resume_from_disk(saved_profiles[0]['encoded_session_id'])
            await test_agents(resumed_id)
        
        # Test 10: Delete session
        test_delete_session(session_ids[2])
        
        # Final: List active sessions
        print_header("FINAL: LIST ALL ACTIVE SESSIONS")
        test_list_active_sessions([])
        
        print_success("All tests completed!")
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())