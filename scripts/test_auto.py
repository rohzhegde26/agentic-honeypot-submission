import asyncio
import httpx
import time

async def test_auto_pilot():
    print("Testing /api/chat/auto...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "sessionId": "test-auto-scenario-123",
            "scenarioType": "bank_fraud"
        }
        start = time.time()
        response = await client.post("http://127.0.0.1:8000/api/chat/auto", json=payload)
        end = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken: {end - start:.2f}s")
        if response.status_code == 200:
            data = response.json()
            print("Response JSON:")
            print(f"Scammer Message: {data.get('scammer_message')}")
            print(f"Honeypot Reply: {data.get('honeypot_reply')}")
            print(f"Scam Detected: {data.get('scamDetected')}")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_auto_pilot())
