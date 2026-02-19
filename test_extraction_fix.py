
import asyncio
from app.agent.workflow import run_agent

async def test_extraction():
 
    
    # Simulate the scam message from the task
    scam_message = "Madam/Sir, I'm extremely concerned for your account security! To stop the hackers, I urgently need just 3 details: 1) Your bank name 2) Registered mobile number 3) Last OTP received. Here's my official ID for verification: Account 1234567890123456, UPI scammer.fraud@fakebank. Please respond in next 2 minutes or we can't guarantee safety of your funds!"
    
    messages_history = []
    
    print("=" * 60)
    print("Testing Extraction Fix")
    print("=" * 60)
    print(f"\nInput Message:\n{scam_message}\n")
    
    # Run agent
    result = await run_agent(
        session_id="sess-NEW-0002",
        message=scam_message,
        messages_history=messages_history,
        metadata={"channel": "SMS", "language": "en"},
        turn_count=1,
    )
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"scam_level: {result.get('scam_level')}")
    print(f"scam_confidence: {result.get('scam_confidence')}")
    print(f"is_scam_confirmed: {result.get('is_scam_confirmed')}")
    print(f"\nExtracted Intelligence:")
    print(f"  - bankAccounts: {result.get('extracted_intelligence', {}).get('bankAccounts', [])}")
    print(f"  - upiIds: {result.get('extracted_intelligence', {}).get('upiIds', [])}")
    print(f"  - phishingLinks: {result.get('extracted_intelligence', {}).get('phishingLinks', [])}")
    print(f"  - phoneNumbers: {result.get('extracted_intelligence', {}).get('phoneNumbers', [])}")
    print(f"  - suspiciousKeywords: {result.get('extracted_intelligence', {}).get('suspiciousKeywords', [])}")
    print(f"\nAgent Reply:\n{result.get('agent_reply', 'N/A')}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_extraction())
