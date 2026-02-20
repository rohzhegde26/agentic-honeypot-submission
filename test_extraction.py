import asyncio
import json
from app.agent.nodes.extractor import _parse_llm_extraction
from app.core.rules import EXTRACT_SYSTEM_PROMPT, STAFF_ID_PATTERN, CASE_ID_PATTERN, ORDER_NUMBER_PATTERN, BANK_ACCOUNT_PATTERN

def test_regex():
    print("--- REGEX TESTS ---")
    
    # Bank Account
    assert BANK_ACCOUNT_PATTERN.search("55678901234567").group() == "55678901234567"
    assert BANK_ACCOUNT_PATTERN.search("10987654321098").group() == "10987654321098"
    print("✅ Bank Accounts pass")
    
    # Secondary IDs
    assert CASE_ID_PATTERN.search("case id: EB-20241587").group(1) == "EB-20241587"
    assert CASE_ID_PATTERN.search("Case No CUS-IND-2024-56789").group(1) == "CUS-IND-2024-56789"
    print("✅ Case IDs pass")
    
    assert ORDER_NUMBER_PATTERN.search("order no: AMZ-9847362").group(1) == "AMZ-9847362"
    assert ORDER_NUMBER_PATTERN.search("Order ID FK-ORD-9283746").group(1) == "FK-ORD-9283746"
    print("✅ Order Numbers pass")


def test_llm_parse():
    print("\n--- LLM PARSER TESTS ---")
    mock_llm_response = '''
    ```json
    {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "bankAccounts": ["55678901234567"],
        "scammerNames": ["Agent Suresh"],
        "staffIds": [],
        "emailAddresses": [],
        "agentNotes": "Found Case ID: EB-20241587, Policy: LIC-1234"
    }
    ```
    '''
    
    result = _parse_llm_extraction(mock_llm_response)
    print("Parsed output:", json.dumps(result, indent=2))
    assert result["agentNotes"] == "Found Case ID: EB-20241587, Policy: LIC-1234"
    print("✅ LLM agentNotes parse pass")


if __name__ == "__main__":
    test_regex()
    test_llm_parse()
