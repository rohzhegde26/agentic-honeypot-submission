
import asyncio
import json
from src.agent.nodes.extractor import extractor_node
from src.agent.nodes.persona import persona_node
from src.agent.state import AgentState

async def run_scenario_test(name, initial_msg, expected_intel_keys):
    print(f"\n--- Testing Scenario: {name} ---")
    
    # 1. Test Extraction from Initial Message
    state: AgentState = {
        "current_user_message": initial_msg,
        "messages": [],
        "extracted_intelligence": {},
        "turn_count": 1
    }
    
    extract_result = await extractor_node(state)
    intel = extract_result.get("extracted_intelligence", {})
    
    print("Initial Extraction:")
    found_any = False
    for key in expected_intel_keys:
        if intel.get(key):
            print(f"  [FOUND] {key}: {intel[key]}")
            found_any = True
    if not found_any:
        print("  [NOT FOUND] No target intel found in initial message (likely requires multi-turn or is purely descriptive)")

    # 2. Test Persona Response (Phase 1: Hook)
    persona_result = await persona_node(state)
    print(f"Persona Reply (Turn 1): {persona_result['agent_reply']}")
    
    # 3. Test High-Turn Baiting (Phase 3: Leak/Bait)
    state["turn_count"] = 8
    state["messages"] = [
        {"sender": "scammer", "text": initial_msg},
        {"sender": "agent", "text": persona_result["agent_reply"]},
        {"sender": "scammer", "text": "Hurry up! Send it now!"}
    ]
    state["current_user_message"] = "Are you doing it or not? Provide your details immediately!"
    
    bait_result = await persona_node(state)
    print(f"Persona Reply (Turn 8 Baiting): {bait_result['agent_reply']}")
    
    # Check if a probe/baiting was included
    reply = bait_result["agent_reply"].lower()
    probes = ["official upi", "manager", "staff id", "employee id", "your name", "verify", "department", "dairy", "son"]
    if any(p in reply for p in probes):
        print("[SUCCESS] Persona triggered a strategic probe/bait.")
    else:
        print("[FAILURE] Persona response did not contain a strategic probe.")

async def main():
    scenarios = [
        {
            "name": "Bank Fraud",
            "msg": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity.",
            "keys": ["bankAccounts"]
        },
        {
            "name": "UPI Fraud",
            "msg": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. This is from official customer support.",
            "keys": ["upiIds"]
        },
        {
            "name": "Phishing Link",
            "msg": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes!",
            "keys": ["phishingLinks"]
        }
    ]
    
    for s in scenarios:
        await run_scenario_test(s["name"], s["msg"], s["keys"])

if __name__ == "__main__":
    asyncio.run(main())
