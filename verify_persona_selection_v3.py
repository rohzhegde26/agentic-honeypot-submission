import os
import sys
from fastapi.testclient import TestClient
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

from app.main import app
from app.services.session_manager import get_session_manager

client = TestClient(app)

def verify_persona_randomization():
    print("=" * 60)
    print("Verifying Persona Randomization via TestClient")
    print("=" * 60)
    
    personas_found = set()
    phone_numbers = set()
    
    # We need to bypass the actual agent run to avoid LLM calls
    # but the session creation happens in routes.py
    
    for i in range(1, 6):
        session_id = f"test-client-session-{i}"
        
        # We can use /health or something if we just want to check setup,
        # but the logic is in /webhook.
        # We will hit /webhook and let it fail on agent run if needed, 
        # as long as the session is created first.
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": "Hi",
                "timestamp": datetime.now().isoformat()
            },
            "metadata": {"channel": "SMS", "language": "en", "locale": "IN"}
        }
        
        # Note: This will actually call the agent unless we mock it.
        # But we can check the session in Redis/fallback immediately after.
        response = client.post("/webhook", json=payload)
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        session_manager = get_session_manager()
        session = loop.run_until_complete(session_manager.get_session(session_id))
        
        if session:
            print(f"Session {i}: Name={session.persona_name}, Phone={session.fake_phone}")
            personas_found.add(session.persona_name)
            phone_numbers.add(session.fake_phone)
            
            # Cleanup
            loop.run_until_complete(session_manager.delete_session(session_id))
        loop.close()

    print("\nResults:")
    print(f"Unique Personas Found: {len(personas_found)} / 5")
    print(f"Unique Phone Numbers Found: {len(phone_numbers)} / 5")
    
    if len(personas_found) > 1 and len(phone_numbers) == 5:
        print("\nSUCCESS: Identities are being randomized effectively.")
    else:
        print("\nFAILURE: Identity randomization lacks sufficient entropy.")

if __name__ == "__main__":
    verify_persona_randomization()
