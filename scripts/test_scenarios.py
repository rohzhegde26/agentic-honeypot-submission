"""
Validate extraction + detection against the 3 evaluator scenarios.
Tests extraction output JSON shape and content matching scorer expectations.
No LLM/server required — runs offline against extractor and detector nodes.
"""
import os
import sys
import json
import asyncio
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

# Disable LLM extraction for deterministic tests
os.environ["FLAG_LLM_EXTRACTION"] = "false"

from app.agent.nodes.extractor import extractor_node
from app.agent.nodes.detector import detector_node


SCENARIOS = [
    {
        "scenarioId": "bank_fraud",
        "initialMessage": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity. Call +91-9876543210 or pay to scammer.fraud@fakebank. Account: 1234567890123456",
        "expected_detection": "confirmed",
        "expected_intel": {
            "phoneNumbers": ["+91-9876543210", "9876543210"],
            "upiIds": ["scammer.fraud@fakebank"],
            "bankAccounts": ["1234567890123456"],
        },
    },
    {
        "scenarioId": "upi_fraud",
        "initialMessage": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. Send Rs 1 to cashback.scam@fakeupi. Call +91-8765432109.",
        "expected_detection": "confirmed",
        "expected_intel": {
            "phoneNumbers": ["+91-8765432109", "8765432109"],
            "upiIds": ["cashback.scam@fakeupi"],
        },
    },
    {
        "scenarioId": "phishing_link",
        "initialMessage": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes! Contact offers@fake-amazon-deals.com",
        "expected_detection": "suspected",  # No confirmed keywords like UPI/OTP in initial msg
        "expected_intel": {
            "phishingLinks": ["http://amaz0n-deals.fake-site.com/claim?id=12345"],
            "emailAddresses": ["offers@fake-amazon-deals.com"],
        },
    },
]

# Fields that should be in extractedIntelligence
SCORER_FIELDS = {"bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "emailAddresses", "suspiciousKeywords"}
# Fields that should NOT be in extractedIntelligence
BANNED_FIELDS = {"staffIds", "scammerNames", "ifscCodes", "panNumbers", "sebiHandles"}


async def run_scenario(scenario):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['scenarioId']}")
    print(f"{'='*60}")

    state = {
        "current_user_message": scenario["initialMessage"],
        "messages": [],
        "extracted_intelligence": {
            "bankAccounts": [], "upiIds": [], "phishingLinks": [],
            "phoneNumbers": [], "emailAddresses": [], "suspiciousKeywords": [],
        },
        "agent_notes": "",
        "scam_level": "safe",
        "scam_confidence": 0.1,
        "is_scam_confirmed": False,
    }

    errors = []

    # 1. Run detector
    det_result = await detector_node(state)
    detection = det_result.get("scam_level", "safe")
    expected_det = scenario["expected_detection"]

    if detection == expected_det:
        print(f"  [PASS] Detection: {detection} (expected {expected_det})")
    else:
        msg = f"  [FAIL] Detection: {detection} (expected {expected_det})"
        print(msg)
        errors.append(msg)

    # 2. Run extractor
    ext_result = await extractor_node(state)
    intel = ext_result["extracted_intelligence"]

    print(f"\n  Extracted Intelligence:")
    print(f"  {json.dumps(intel, indent=4)}")

    # 3. Check schema compliance
    extra_keys = set(intel.keys()) - SCORER_FIELDS
    if extra_keys:
        msg = f"  [FAIL] Extra keys in intel: {extra_keys}"
        print(msg)
        errors.append(msg)
    else:
        print(f"  [PASS] Schema: only scorer-expected fields present")

    banned = set(intel.keys()) & BANNED_FIELDS
    if banned:
        msg = f"  [FAIL] Banned fields in intel: {banned}"
        print(msg)
        errors.append(msg)

    # 4. Check expected extractions
    for field, expected_values in scenario["expected_intel"].items():
        actual = intel.get(field, [])
        for val in expected_values:
            if val in actual:
                print(f"  [PASS] {field} contains '{val}'")
            else:
                msg = f"  [FAIL] {field} missing '{val}' (actual: {actual})"
                print(msg)
                errors.append(msg)

    # 5. Check UPI doesn't contain emails
    for upi in intel.get("upiIds", []):
        domain = upi.split("@")[1] if "@" in upi else ""
        if "." in domain:
            msg = f"  [FAIL] Email in UPI list: {upi}"
            print(msg)
            errors.append(msg)

    # 6. Check agent notes for extra intel
    notes = ext_result.get("agent_notes", "")
    if notes:
        print(f"\n  Agent Notes: {notes}")

    return errors


async def main():
    print("=" * 60)
    print("HONEYPOT SCENARIO VALIDATION")
    print("=" * 60)

    all_errors = []
    for scenario in SCENARIOS:
        errors = await run_scenario(scenario)
        all_errors.extend(errors)

    print(f"\n{'='*60}")
    if all_errors:
        print(f"[FAIL] {len(all_errors)} ERRORS FOUND:")
        for e in all_errors:
            print(f"  {e}")
    else:
        print("[PASS] ALL 3 SCENARIOS PASSED")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
