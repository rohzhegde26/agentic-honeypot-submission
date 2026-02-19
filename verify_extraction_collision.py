import sys
import os
import re

# Setup paths
sys.path.append(os.getcwd())

from app.agent.nodes.extractor import _extract_phone_numbers, _extract_bank_accounts

def test_91_prefix_extraction():
    print("=" * 60)
    print("Testing 91-Prefix Extraction & Collision Prevention")
    print("=" * 60)
    
    test_cases = [
        {
            "text": "Send money to 919876543210 immediately",
            "expected_phone": ["9876543210"],
            "expected_bank": []
        },
        {
            "text": "Account number is 1234567890123456",
            "expected_phone": [],
            "expected_bank": ["1234567890123456"]
        },
        {
            "text": "Call me on +91 7890123456 or transfer to bank 919876543210",
            "# Comment": "Wait, if 919876543210 is a phone, it should be a phone.",
            "expected_phone": ["7890123456", "9876543210"],
            "expected_bank": []
        }
    ]
    
    for i, case in enumerate(test_cases):
        text = case["text"]
        phones = _extract_phone_numbers(text)
        banks = _extract_bank_accounts(text)
        
        print(f"\nTest Case {i+1}: '{text}'")
        print(f"Extracted Phones: {phones}")
        print(f"Extracted Banks:  {banks}")
        
        # In the context of the full extractor_node, phones are removed from banks.
        # But _extract_bank_accounts has its own 91-prefix skip logic now.
        
        phone_match = set(phones) == set(case["expected_phone"])
        bank_match = set(banks) == set(case["expected_bank"])
        
        if phone_match and bank_match:
            print("RESULT: PASS")
        else:
            print("RESULT: FAIL")
            if not phone_match: print(f"  Phone Mismatch: Expected {case['expected_phone']}")
            if not bank_match: print(f"  Bank Mismatch: Expected {case['expected_bank']}")

if __name__ == "__main__":
    test_91_prefix_extraction()
