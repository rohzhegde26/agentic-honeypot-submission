import requests
import json
import time
from datetime import datetime
import os

# Test the API structure matches the new evaluation guidelines
# 20 Points depend on: scamDetected, extractedIntelligence, engagementMetrics, agentNotes being present.

url = "http://localhost:7860/api/chat/demo"
payload = {
    "sessionId": "scoring-test-session",
    "message": {
        "sender": "scammer",
        "text": "Hi, I am Sharma from SBI. Your KYC is expired. Share your email and UPI ID. scammer@gmail.com, test@upi",
        "timestamp": datetime.utcnow().isoformat()
    }
}

print("--- Testing Scoring Structure Compliance ---")
try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse structure:")
        print(json.dumps(data, indent=2))
        
        # Validation checks
        required_fields = ["scamDetected", "extractedIntelligence", "engagementMetrics", "agentNotes"]
        missing = [f for f in required_fields if f not in data]
        
        if not missing:
            print("\n✅ SUCCESS: All scoring fields present (20/20 structure points)")
        else:
            print(f"\n❌ FAILURE: Missing fields: {missing}")
            
        # Check email extraction
        intel = data.get("extractedIntelligence", {})
        emails = intel.get("emailAddresses", [])
        if "scammer@gmail.com" in emails:
            print("✅ SUCCESS: Email extraction working")
        else:
            print(f"❌ FAILURE: Email extraction failed. Found: {emails}")
            
except Exception as e:
    print(f"Error: {e}")
