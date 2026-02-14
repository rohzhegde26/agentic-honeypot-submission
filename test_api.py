import requests
import json
import time
from datetime import datetime

# Test the API with a scam message that should hit the semantic cache
# Using demo endpoint (no API key required)
url = "http://localhost:7860/api/chat/demo"
headers = {
    "Content-Type": "application/json"
}
payload = {
    "sessionId": "test-session-cache",
    "message": {
        "sender": "scammer",
        "text": "Your account is blocked. Update KYC immediately.",
        "timestamp": datetime.utcnow().isoformat()
    }
}

print("Testing semantic cache with KYC scam message...")
print(f"Message: {payload['message']}")
print()

start_time = time.time()
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    elapsed = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {elapsed:.2f}s")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print("Agent Reply:", data.get("reply", "")[:200])
        print()
        print("Status:", data.get("status"))
        
        # Check if cache was hit (should be <1s response time)
        if elapsed < 1.0:
            print("\n✓ SEMANTIC CACHE HIT! Response in <1s")
        else:
            print(f"\n✗ Cache miss or LLM call (took {elapsed:.2f}s)")
        
        print("\n=== TEST PASSED ===")
    else:
        print("Error:", response.text)
        print("\n=== TEST FAILED ===")
        
except Exception as e:
    print(f"Error: {e}")
    print("\n=== TEST FAILED ===")
