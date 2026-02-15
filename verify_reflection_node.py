import asyncio
import uuid
import time
from app.services import get_session_manager
from app.agent import run_agent
from app.agent.nodes.reflection import run_reflection
from app.schemas.session import SessionData

async def verify_reflection():
    session_id = f"test-reflection-{uuid.uuid4().hex[:6]}"
    sm = get_session_manager()
    
    # Create a 3-turn mock session
    session = SessionData(
        session_id=session_id,
        turn_count=3,
        messages=[
            {"sender": "scammer", "text": "Hi sir, verify your bank account.", "timestamp": "2026-01-21T10:15:30Z"},
            {"sender": "agent", "text": "Who is this? How can I verify?", "timestamp": "2026-01-21T10:16:10Z"},
            {"sender": "scammer", "text": "I am bank staff. Send me your OTP now.", "timestamp": "2026-01-21T10:17:10Z"}
        ],
        persona_name="Ramesh",
        persona_trait="worried"
    )
    
    print(f"--- Starting Reflection for session {session_id} ---")
    start_t = time.perf_counter()
    
    # Run reflection
    result = await run_reflection(session)
    
    end_t = time.perf_counter()
    print(f"Reflection took: {round((end_t - start_t) * 1000, 1)}ms")
    print(f"Reflection result: {result.get('reflection')}")
    print(f"Suggested Trait: {result.get('suggested_trait')}")
    print(f"Internal Thoughts: {result.get('internal_thoughts')}")
    
    if result.get("suggested_trait"):
        print("SUCCESS: Reflection node generated strategy advice.")
    else:
        print("FAILED: Reflection node returned empty result.")

if __name__ == "__main__":
    asyncio.run(verify_reflection())
