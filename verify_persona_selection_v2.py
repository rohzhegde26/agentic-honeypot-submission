import asyncio
import sys
import logging
from datetime import datetime

# Setup paths
import os
sys.path.append(os.getcwd())

from app.schemas.message import WebhookRequest, MessageInput
from app.core.routes import webhook
from app.services.session_manager import get_session_manager

# Mock BackgroundTasks
class MockBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        pass

async def verify_persona_randomization():
    print("=" * 60)
    print("Verifying Persona Randomization and Identity Uniqueness")
    print("=" * 60)
    
    session_manager = get_session_manager()
    personas_found = set()
    phone_numbers = set()
    
    for i in range(1, 6):
        session_id = f"verification-session-{i}-{datetime.now().timestamp()}"
        
        request = WebhookRequest(
            sessionId=session_id,
            message=MessageInput(sender="scammer", text="Hi", timestamp=datetime.now()),
            metadata={"channel": "SMS", "language": "en", "locale": "IN"}
        )
        
        # We need to mocker the run_agent if we don't want to call LLM
        # But here we just want to see if the session is CREATED with correct persona
        # The Persona is assigned BEFORE run_agent in routes.py
        
        # Mocking run_agent to avoid LLM costs
        import app.core.routes as routes_module
        async def mock_run_agent(**kwargs):
            return {"agent_reply": "Mock", "timing_log": []}
        
        original_run_agent = routes_module.run_agent
        routes_module.run_agent = mock_run_agent
        
        try:
            await webhook(request, MockBackgroundTasks())
            
            # Retrieve the created session
            session = await session_manager.get_session(session_id)
            if session:
                print(f"Session {i}: Name={session.persona_name}, Phone={session.fake_phone}")
                personas_found.add(session.persona_name)
                phone_numbers.add(session.fake_phone)
        finally:
            routes_module.run_agent = original_run_agent
            await session_manager.delete_session(session_id)

    print("\nResults:")
    print(f"Unique Personas Found: {len(personas_found)} / 5")
    print(f"Unique Phone Numbers Found: {len(phone_numbers)} / 5")
    
    if len(personas_found) > 1 and len(phone_numbers) == 5:
        print("\nSUCCESS: Identities are being randomized effectively.")
    else:
        print("\nFAILURE: Identity randomization lacks sufficient entropy.")

if __name__ == "__main__":
    asyncio.run(verify_persona_randomization())
