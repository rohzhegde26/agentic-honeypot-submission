import os
import sys
from fastapi.testclient import TestClient
from datetime import datetime
import asyncio

# Setup paths
sys.path.append(os.getcwd())

from app.main import app
from app.services.session_manager import get_session_manager
from app.config import get_settings

client = TestClient(app)
settings = get_settings()
API_KEY = settings.API_SECRET_KEY

def verify_persona_randomization():
    print("=" * 60)
    print("Verifying Persona Randomization via TestClient")
    print("=" * 60)
    
    personas_found = set()
    phone_numbers = set()
    
    for i in range(1, 6):
        session_id = f"test-client-session-{i}-{int(datetime.now().timestamp())}"
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": "Hi",
                "timestamp": datetime.now().isoformat()
            },
            "metadata": {"channel": "SMS", "language": "en", "locale": "IN"}
        }
        
        # Hit webhook with proper API key
        response = client.post(
            "/webhook", 
            json=payload,
            headers={"x-api-key": API_KEY}
        )
        
        if response.status_code != 200:
            print(f"Error session {i}: {response.status_code} - {response.text}")
            continue
            
        # Check the session state directly in Redis/Fallback
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
