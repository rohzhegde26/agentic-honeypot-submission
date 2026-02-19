import asyncio
import sys
import os

# Setup paths
sys.path.append(os.getcwd())

from app.agent.nodes.extractor import extractor_node
from app.agent.state import AgentState

async def verify_extractor_integration():
    print("=" * 60)
    print("Verifying Extractor Node Integration")
    print("=" * 60)
    
    test_data = [
        {
            "msg": "Send to 919876543210 now",
            "expect_phone": "9876543210"
        },
        {
            "msg": "Transfer to Account 1234567899123456 please",
            "expect_bank": "1234567899123456"
        },
        {
            "msg": "Call 91 7890123456 or bank 919876543210",
            "expect_phones": ["7890123456", "9876543210"]
        }
    ]
    
    for item in test_data:
        msg = item["msg"]
        state: AgentState = {
            "current_user_message": msg,
            "messages": [],
            "extracted_intelligence": {},
            "persona_name": "Ramesh",
            "fake_phone": "9999999999"
        }
        
        # Disable LLM for deterministic regex testing
        from app.config import get_settings
        settings = get_settings()
        settings.FLAG_LLM_EXTRACTION = False
        
        result = await extractor_node(state)
        intel = result["extracted_intelligence"]
        
        print(f"\nMessage: '{msg}'")
        print(f"Phones: {intel.get('phoneNumbers')}")
        print(f"Banks:  {intel.get('bankAccounts')}")
        
        if "expect_phone" in item:
            if item["expect_phone"] not in intel.get("phoneNumbers", []):
                print(f"FAIL: Expected phone {item['expect_phone']}")
            else:
                print("PASS: Phone extracted")

        if "expect_phones" in item:
            if not all(p in intel.get("phoneNumbers", []) for p in item["expect_phones"]):
                 print(f"FAIL: Expected phones {item['expect_phones']}")
            else:
                print("PASS: Both phones extracted")
        
        if "expect_bank" in item:
            if item["expect_bank"] not in intel.get("bankAccounts", []):
                print(f"FAIL: Expected bank {item['expect_bank']}")
            else:
                print("PASS: Bank account extracted")

    # Final Boundary Check: 12-digit number that IS a bank account
    msg = "Ac no 1234567654321098" # 7654321098 ends it, but no start boundary
    state["current_user_message"] = msg
    result = await extractor_node(state)
    intel = result["extracted_intelligence"]
    print(f"\nCollision Case: '{msg}'")
    print(f"Phones: {intel.get('phoneNumbers')}")
    print(f"Banks:  {intel.get('bankAccounts')}")
    if "7654321098" in intel.get("phoneNumbers", []):
        print("FAIL: Sliced phone number from bank account!")
    else:
        print("PASS: No sliced phone number found.")

if __name__ == "__main__":
    asyncio.run(verify_extractor_integration())
