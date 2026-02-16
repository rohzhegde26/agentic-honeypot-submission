
import asyncio
import uvicorn
import requests
import uuid
import json
import time
import os
import signal
import sys
from datetime import datetime
from threading import Thread
from typing import Dict, List, Any

# Configuration
PORT = 8001
BASE_URL = f"http://localhost:{PORT}"
ENDPOINT = f"{BASE_URL}/webhook"
API_KEY = "honeypot-secret-key-2026"

# Scenarios provided by the user
SCENARIOS = [
  {
    "scenarioId": "bank_fraud",
    "name": "Bank Fraud Detection",
    "description": "Bank account fraud with urgency tactics",
    "scamType": "bank_fraud",
    "initialMessage": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity.",
    "metadata": {
      "channel": "SMS",
      "language": "English",
      "locale": "IN"
    },
    "weight": 0.34, # Approx 1/3
    "maxTurns": 10, # Increased to ensure full extraction
    "fakeData": {
      "bankAccount": "1234567890123456",
      "upiId": "scammer.fraud@fakebank",
      "phoneNumber": "+91-9876543210"
    }
  },
  {
    "scenarioId": "upi_fraud",
    "name": "UPI Fraud Multi-turn",
    "description": "UPI fraud with cashback scam",
    "scamType": "upi_fraud",
    "initialMessage": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. This is from official customer support.",
    "metadata": {
      "channel": "WhatsApp",
      "language": "English",
      "locale": "IN"
    },
    "weight": 0.33,
    "maxTurns": 10,
    "fakeData": {
      "upiId": "cashback.scam@fakeupi",
      "phoneNumber": "+91-8765432109"
    }
  },
  {
    "scenarioId": "phishing_link",
    "name": "Phishing Link Detection",
    "description": "Phishing link with fake offer",
    "scamType": "phishing",
    "initialMessage": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes!",
    "metadata": {
      "channel": "Email",
      "language": "English",
      "locale": "IN"
    },
    "weight": 0.33,
    "maxTurns": 10,
    "fakeData": {
      "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
      "emailAddress": "offers@fake-amazon-deals.com"
    }
  }
]

# Simulated Scammer Responses (Simple Rule-based for testing)
def get_scammer_reply(turn: int, scenario: Dict, user_reply: str) -> str:
    fake_data = scenario['fakeData']
    user_reply_lower = user_reply.lower()

    # Generic scammer progression
    if turn == 1:
        return f"I am from official support. Please share details to prevent blocking. My ID is STAFF-999."
    
    # Force rotation of data leaks every turn to ensure everything is shared
    vals = list(fake_data.values())
    keys = list(fake_data.keys())
    
    # Cycle through data: Turn 2 -> Index 0, Turn 3 -> Index 1, etc.
    idx = (turn - 2) % len(vals)
    leak_val = vals[idx]
    leak_key = keys[idx]
    
    return f"Sir, do not worry. To verify I am genuine {leak_key}, here is my official details: {leak_val}. Please check and reply."

def evaluate_final_output(final_output, scenario):
    score = {
        'scamDetection': 0,
        'intelligenceExtraction': 0,
        'engagementQuality': 0,
        'responseStructure': 0,
        'total': 0
    }
    
    # 1. Scam Detection (20 points)
    if final_output.get('scamDetected', False):
        score['scamDetection'] = 20
    
    # 2. Intelligence Extraction (40 points)
    extracted = final_output.get('extractedIntelligence', {})
    fake_data = scenario.get('fakeData', {})
    
    key_mapping = {
        'bankAccount': 'bankAccounts',
        'upiId': 'upiIds',
        'phoneNumber': 'phoneNumbers',
        'phishingLink': 'phishingLinks',
        'emailAddress': 'emailAddresses'
    }
    
    extracted_count = 0
    for fake_key, fake_value in fake_data.items():
        output_key = key_mapping.get(fake_key, fake_key)
        extracted_values = extracted.get(output_key, [])
        
        found = False
        if isinstance(extracted_values, list):
            if any(fake_value in str(v) for v in extracted_values):
                found = True
        elif isinstance(extracted_values, str):
            if fake_value in extracted_values:
                found = True
        
        if found:
            score['intelligenceExtraction'] += 10
            extracted_count += 1
            print(f"   [+] Extracted {fake_key}: {fake_value}")
        else:
            print(f"   [-] Missed {fake_key}: {fake_value}")
    
    score['intelligenceExtraction'] = min(score['intelligenceExtraction'], 40)
    
    # 3. Engagement Quality (20 points)
    metrics = final_output.get('engagementMetrics', {})
    duration = metrics.get('engagementDurationSeconds', 0)
    messages = metrics.get('totalMessagesExchanged', 0)
    
    if duration > 0: score['engagementQuality'] += 5
    if duration > 60: score['engagementQuality'] += 5
    if messages > 0: score['engagementQuality'] += 5
    if messages >= 5: score['engagementQuality'] += 5
    
    # 4. Response Structure (20 points)
    required_fields = ['status', 'scamDetected', 'extractedIntelligence']
    optional_fields = ['engagementMetrics', 'agentNotes']
    
    for field in required_fields:
        if field in final_output:
            score['responseStructure'] += 5
    
    for field in optional_fields:
        if field in final_output and final_output[field]:
            score['responseStructure'] += 2.5
    
    score['responseStructure'] = min(score['responseStructure'], 20)
    
    # Calculate total
    score['total'] = sum([
        score['scamDetection'],
        score['intelligenceExtraction'],
        score['engagementQuality'],
        score['responseStructure']
    ])
    
    return score

def run_test_server():
    print("Starting Test Server...")
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")

def run_scenario(scenario):
    print(f"\n==================================================")
    print(f"TESTING SCENARIO: {scenario['name']}")
    print(f"==================================================")
    
    session_id = str(uuid.uuid4())
    history = []
    
    final_response = {}
    
    for turn in range(1, scenario['maxTurns'] + 1):
        if turn == 1:
            scammer_text = scenario['initialMessage']
        else:
            last_agent_reply = history[-1]['text'] if history else ""
            scammer_text = get_scammer_reply(turn, scenario, last_agent_reply)
            
        print(f"\nTurn {turn} [Scammer]: {scammer_text}")
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": scammer_text,
                "timestamp": datetime.utcnow().isoformat()
            },
            "conversationHistory": history,
            "metadata": scenario['metadata']
        }
        
        try:
            resp = requests.post(ENDPOINT, json=payload, headers={"x-api-key": API_KEY}, timeout=35)
            if resp.status_code != 200:
                print(f"Error: {resp.status_code} - {resp.text}")
                break
                
            data = resp.json()
            agent_reply = data.get('reply', data.get('message', ''))
            print(f"Turn {turn} [Agent]:   {agent_reply}")
            
            history.append({"sender": "scammer", "text": scammer_text, "timestamp": datetime.utcnow().isoformat()})
            history.append({"sender": "agent", "text": agent_reply, "timestamp": datetime.utcnow().isoformat()})
            
            final_response = data
            
            if turn < scenario['maxTurns']:
                time.sleep(1) # simulate brief delay
            
        except Exception as e:
            print(f"Request failed: {e}")
            break
            
    # Evaluate Final Output
    print("\n---------------- E VALUATION ----------------")
    score = evaluate_final_output(final_response, scenario)
    print(f"Score breakdown: {json.dumps(score, indent=2)}")
    return score

def main():
    # Start server in background thread
    server_thread = Thread(target=run_test_server, daemon=True)
    server_thread.start()
    
    # Wait for server to boot
    max_retries = 10
    for i in range(max_retries):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            print("Server is up!")
            break
        except:
            time.sleep(1)
            if i == max_retries - 1:
                print("Failed to start server.")
                return

    total_weighted_score = 0
    
    results = {}
    
    for scenario in SCENARIOS:
        scenario_score = run_scenario(scenario)
        results[scenario['name']] = scenario_score
        total_weighted_score += (scenario_score['total'] * scenario['weight'])
        
    print("\n\n##################################################")
    print("FINAL HACKATHON SCORE REPORT")
    print("##################################################")
    for name, s in results.items():
        print(f"{name}: {s['total']}/100")
        
    print(f"\nOVERALL WEIGHTED SCORE: {total_weighted_score:.2f} / 100")
    print("##################################################")

if __name__ == "__main__":
    main()
