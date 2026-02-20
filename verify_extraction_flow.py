
import asyncio
import re
from app.agent.nodes.extractor import extractor_node
from app.agent.state import AgentState

async def test_extraction():
    print("--- Testing Extraction Flow ---")
    
    # Dialogue from user's logs
    messages = [
        {"sender": "scammer", "text": "URGENT: Your SBI account has been compromised... Share your account number and OTP immediately"},
        {"sender": "agent", "text": "OTP? You mean the SMS code? ... Are you really from the bank?"},
        {"sender": "scammer", "text": "Yes, this is the SBI security team. Please send your account number (1234567890123456) and the OTP you just received"},
        {"sender": "agent", "text": "Wait wait. My account number is different. I have 52627951029193. And no OTP came to my phone yet."},
        {"sender": "scammer", "text": "Your account is flagged; the OTP will arrive in seconds—send it immediately along with your UPI PIN"},
        {"sender": "agent", "text": "UPI PIN? No no... Why you asking for PIN?"},
        {"sender": "scammer", "text": "Your account will be locked in minutes; please send the OTP you receive and your UPI PIN to +91-9876543210 right now"},
    ]
    
    state: AgentState = {
        "current_user_message": messages[-1]["text"],
        "messages": messages[:-1],
        "extracted_intelligence": {},
        "turn_count": len(messages) // 2
    }
    
    print(f"Testing message: {state['current_user_message']}")
    result = await extractor_node(state)
    
    intel = result.get("extracted_intelligence", {})
    print("\nExtracted Intelligence:")
    for key, val in intel.items():
        if val:
            print(f"  {key}: {val}")
            
    # Verify phone extraction
    phones = intel.get("phoneNumbers", [])
    if "9876543210" in phones:
        print("\n[OK] SUCCESS: Phone number 9876543210 extracted correctly.")
    else:
        print("\n[FAIL] FAILURE: Phone number 9876543210 NOT extracted.")
        
    # Verify account extraction
    accounts = intel.get("bankAccounts", [])
    if "1234567890123456" in accounts:
        print("[OK] SUCCESS: Bank account 1234567890123456 extracted correctly.")
    else:
        # Check Turn 2 message as well
        state["current_user_message"] = messages[2]["text"]
        result2 = await extractor_node(state)
        intel2 = result2.get("extracted_intelligence", {})
        if "1234567890123456" in intel2.get("bankAccounts", []):
            print("[OK] SUCCESS: Bank account extracted from historical turns correctly.")
        else:
            print("[FAIL] FAILURE: Bank account 1234567890123456 NOT extracted.")

if __name__ == "__main__":
    asyncio.run(test_extraction())
