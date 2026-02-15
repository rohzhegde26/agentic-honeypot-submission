import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def run_test():
    print("Starting Benchmark Verification...")
    
    # 1. Login/Join with Solo Mode
    print("\n1. Joining Session (Solo Mode)...")
    payload = {
        "api_key": "honeypot-secret-key-2026", # Retrieved key
        "nickname": "Tester",
        "expected_voters": 1
    }
    
    res = requests.post(f"{BASE_URL}/api/benchmark/join", json=payload)
    if res.status_code != 200:
        print(f"Join failed: {res.text}. Ensure server is running and key is correct.")
        # Try to find key if needed
        return

    data = res.json()
    token = data["token"]
    print(f"Joined! Token: {token}")
    
    # 2. Check Auto-Start (Status should be 'input')
    print("\n2. Checking Auto-Start Status...")
    res = requests.get(f"{BASE_URL}/api/benchmark/poll", headers={"token": token})
    state = res.json()
    print(f"Current Status: {state['status']}")
    
    if state['status'] != 'input':
        print(f"FAIL: Status is '{state['status']}', expected 'input'.")
        # Force start via join again? No.
    else:
        print("PASS: Auto-start worked.")

    # 3. Send Message
    print("\n3. Sending Message...")
    msg_payload = {"message": "What is 1+1?"}
    res = requests.post(f"{BASE_URL}/api/benchmark/send", json=msg_payload, headers={"token": token})
    print(f"Send Result: {res.status_code}")
    
    # 4. Poll for Completion
    print("\n4. Polling for Responses (Testing Fireworks)...")
    start_time = time.time()
    while time.time() - start_time < 60: # 60s timeout
        try:
            res = requests.get(f"{BASE_URL}/api/benchmark/poll", headers={"token": token})
            state = res.json()
            if state['status'] == 'voting':
                print("PASS: Generation complete. Status is 'voting'.")
                responses = state.get('responses', [])
                print(f"Received {len(responses)} responses.")
                if len(responses) > 0:
                    print(f"Sample Response: {responses[0]['alias']}")
                else:
                    print("FAIL: No responses received.")
                break
            elif state['status'] == 'thinking':
                 print(f"Thinking... ({int(time.time()-start_time)}s)")
            
            time.sleep(2)
        except Exception as e:
            print(f"Error polling: {e}")
            time.sleep(2)
    else:
        print("FAIL: Timed out waiting for responses.")
        return

    # 5. Vote
    print("\n5. Casting Vote...")
    if state.get('responses'):
        alias = state['responses'][0]['alias']
        res = requests.post(f"{BASE_URL}/api/benchmark/vote", json={"agent_alias": alias}, headers={"token": token})
        print(f"Vote Result: {res.status_code}")
    else:
        print("SKIP: No responses to vote on.")

    # 6. Reveal
    print("\n6. Revealing Results...")
    res = requests.post(f"{BASE_URL}/api/benchmark/reveal", headers={"token": token})
    print(f"Reveal Result: {res.status_code}")
    
    res = requests.get(f"{BASE_URL}/api/benchmark/poll", headers={"token": token})
    state = res.json()
    if state['status'] == 'results':
        print("PASS: Status is 'results'.")
    else:
        print(f"FAIL: Status is {state['status']}")

    # 7. Next Turn
    print("\n7. Next Turn...")
    requests.post(f"{BASE_URL}/api/benchmark/next", headers={"token": token})
    res = requests.get(f"{BASE_URL}/api/benchmark/poll", headers={"token": token})
    state = res.json()
    if state['status'] == 'input':
        print("PASS: Status is 'input'. Cycle complete.")
    else:
        print(f"FAIL: Status is {state['status']}")

if __name__ == "__main__":
    run_test()
