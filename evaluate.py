"""
Comprehensive Pre-Submission Evaluation Script
Tests all critical aspects of the honeypot agent.
"""
import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.agent.workflow import run_agent
from app.agent.nodes.detector import detector_node
from app.agent.nodes.extractor import extractor_node
from app.agent.nodes.persona import persona_node

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test scenarios covering different scam types
TEST_SCENARIOS = [
    {
        "name": "OTP Phishing",
        "message": "URGENT: Your SBI account will be blocked. Share OTP immediately to verify.",
        "expected_scam_level": "confirmed",
        "expected_intel": ["otp", "urgent", "blocked"]
    },
    {
        "name": "UPI Scam",
        "message": "Send Rs 1 to verify-bank@paytm to activate your account or it will be closed.",
        "expected_scam_level": "confirmed",
        "expected_intel": ["verify-bank@paytm"]
    },
    {
        "name": "Phishing Link",
        "message": "Click http://sbi-kyc-update.com to update KYC before deadline.",
        "expected_scam_level": "suspected",
        "expected_intel": ["http://sbi-kyc-update.com", "kyc", "deadline"]
    },
    {
        "name": "Safe Message",
        "message": "Hello, how are you?",
        "expected_scam_level": "safe",
        "expected_intel": []
    },
    {
        "name": "Job Scam",
        "message": "Congratulations! You won lottery of 10 lakh. Call 9876543210 to claim prize.",
        "expected_scam_level": "suspected",
        "expected_intel": ["9876543210", "lottery", "won", "prize"]
    }
]

class Evaluator:
    def __init__(self):
        self.results = {
            "scam_detection": [],
            "intelligence_extraction": [],
            "persona_authenticity": [],
            "response_time": [],
            "overall_score": 0
        }
    
    async def test_scam_detection(self):
        """Test scam detection accuracy."""
        print("\n" + "="*70)
        print("TEST 1: SCAM DETECTION ACCURACY")
        print("="*70)
        
        correct = 0
        total = len(TEST_SCENARIOS)
        
        for scenario in TEST_SCENARIOS:
            state = {
                "current_user_message": scenario["message"],
                "messages": [],
                "scam_confidence": 0.0,
                "is_scam_confirmed": False,
                "scam_level": "safe",
            }
            
            result = await detector_node(state)
            detected_level = result.get("scam_level", "safe")
            
            is_correct = detected_level == scenario["expected_scam_level"]
            correct += 1 if is_correct else 0
            
            status = "[OK]" if is_correct else "[FAIL]"
            print(f"{status} {scenario['name']}: Expected '{scenario['expected_scam_level']}', Got '{detected_level}'")
            
            self.results["scam_detection"].append({
                "scenario": scenario["name"],
                "correct": is_correct
            })
        
        accuracy = (correct / total) * 100
        print(f"\nDetection Accuracy: {accuracy:.1f}% ({correct}/{total})")
        return accuracy
    
    async def test_intelligence_extraction(self):
        """Test intelligence extraction capabilities."""
        print("\n" + "="*70)
        print("TEST 2: INTELLIGENCE EXTRACTION")
        print("="*70)
        
        total_expected = 0
        total_extracted = 0
        
        for scenario in TEST_SCENARIOS:
            state = {
                "current_user_message": scenario["message"],
                "messages": [],
                "extracted_intelligence": {
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": [],
                },
                "agent_notes": "",
            }
            
            result = await extractor_node(state)
            intel = result["extracted_intelligence"]
            
            # Count extracted items
            extracted_count = (
                len(intel["upiIds"]) + 
                len(intel["phoneNumbers"]) + 
                len(intel["phishingLinks"]) +
                len(intel["suspiciousKeywords"])
            )
            
            expected_count = len(scenario["expected_intel"])
            total_expected += expected_count
            total_extracted += min(extracted_count, expected_count)
            
            print(f"\n{scenario['name']}:")
            print(f"  UPI IDs: {intel['upiIds']}")
            print(f"  Phone Numbers: {intel['phoneNumbers']}")
            print(f"  Phishing Links: {intel['phishingLinks']}")
            print(f"  Keywords: {intel['suspiciousKeywords'][:3]}...")  # Show first 3
            
            self.results["intelligence_extraction"].append({
                "scenario": scenario["name"],
                "extracted": extracted_count,
                "expected": expected_count
            })
        
        extraction_rate = (total_extracted / max(total_expected, 1)) * 100
        print(f"\nExtraction Rate: {extraction_rate:.1f}%")
        return extraction_rate
    
    async def test_persona_authenticity(self):
        """Test persona response authenticity."""
        print("\n" + "="*70)
        print("TEST 3: PERSONA AUTHENTICITY")
        print("="*70)
        
        test_message = "Sir your account is blocked. Send OTP to verify."
        
        state = {
            "session_id": "eval-test",
            "current_user_message": test_message,
            "messages": [],
            "scam_confidence": 0.9,
            "is_scam_confirmed": True,
            "scam_level": "confirmed",
            "extracted_intelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": ["otp", "blocked"],
            },
            "turn_count": 1,
            "termination_reason": None,
            "agent_notes": "",
            "agent_reply": "",
            "persona_name": "Ramesh Kumar",
            "persona_age": 67,
            "persona_location": "Pune",
            "persona_background": "retired government employee",
            "persona_occupation": "Ex-Government Clerk",
            "persona_trait": "anxious and very polite",
            "fake_phone": "9876543210",
            "fake_upi": "ramesh@okaxis",
            "fake_bank_account": "123456789012",
            "fake_ifsc": "SBIN0001234",
            "channel": "SMS",
            "language": "en",
            "locale": "IN",
        }
        
        result = await persona_node(state)
        reply = result.get("agent_reply", "")
        
        print(f"\nScammer: {test_message}")
        print(f"Honeypot: {reply}")
        
        # Check authenticity criteria
        checks = {
            "No AI references": "AI" not in reply and "assistant" not in reply.lower(),
            "Plain text (no markdown)": "**" not in reply and "*" not in reply,
            "Short reply (SMS-like)": len(reply) < 200,
            "Contains confusion/politeness": any(word in reply.lower() for word in ["sir", "please", "plese", "confused"]),
            "No immediate data leak": not any(data in reply for data in ["9876543210", "ramesh@okaxis", "123456789012"])
        }
        
        print("\nAuthenticity Checks:")
        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {check}")
        
        authenticity_score = (sum(checks.values()) / len(checks)) * 100
        print(f"\nAuthenticity Score: {authenticity_score:.1f}%")
        
        self.results["persona_authenticity"] = {
            "reply": reply,
            "checks": checks,
            "score": authenticity_score
        }
        
        return authenticity_score
    
    async def test_response_time(self):
        """Test end-to-end response time."""
        print("\n" + "="*70)
        print("TEST 4: RESPONSE TIME (LATENCY)")
        print("="*70)
        
        test_message = "Your account is blocked. Send OTP 123456 to verify@upi immediately."
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                run_agent(
                    session_id="eval-latency-test",
                    message=test_message,
                    messages_history=[],
                    metadata={"channel": "SMS", "language": "en", "locale": "IN"},
                    turn_count=1,
                    existing_intel=None,
                    persona_details=None
                ),
                timeout=30.0
            )
            
            elapsed = time.time() - start_time
            
            print(f"\nTotal Response Time: {elapsed:.2f}s")
            print(f"Reply: {result.get('agent_reply', 'N/A')[:100]}...")
            
            # Evaluate against timeout threshold
            if elapsed < 25:
                status = "[OK] EXCELLENT (< 25s)"
                score = 100
            elif elapsed < 28:
                status = "[GOOD] (< 28s)"
                score = 80
            else:
                status = "[MARGINAL] (> 28s)"
                score = 60
            
            print(f"Status: {status}")
            
            self.results["response_time"] = {
                "elapsed": elapsed,
                "score": score
            }
            
            return score
            
        except asyncio.TimeoutError:
            print("[TIMEOUT] (> 30s)")
            self.results["response_time"] = {
                "elapsed": 30.0,
                "score": 0
            }
            return 0
    
    def test_code_quality(self):
        """Test code quality and structure."""
        print("\n" + "="*70)
        print("TEST 5: CODE QUALITY & STRUCTURE")
        print("="*70)
        
        checks = {
            "Environment variables configured": os.path.exists(".env"),
            "LangGraph workflow defined": os.path.exists("app/agent/workflow.py"),
            "State schema defined": os.path.exists("app/agent/state.py"),
            "Detector node exists": os.path.exists("app/agent/nodes/detector.py"),
            "Extractor node exists": os.path.exists("app/agent/nodes/extractor.py"),
            "Persona node exists": os.path.exists("app/agent/nodes/persona.py"),
            "Output node exists": os.path.exists("app/agent/nodes/output.py"),
            "API routes defined": os.path.exists("app/core/routes.py"),
            "Callback service exists": os.path.exists("app/services/callback_service.py"),
        }
        
        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {check}")
        
        quality_score = (sum(checks.values()) / len(checks)) * 100
        print(f"\nCode Quality Score: {quality_score:.1f}%")
        
        return quality_score
    
    async def run_all_tests(self):
        """Run all evaluation tests."""
        print("\n" + "="*70)
        print("HONEYPOT AGENT - FINAL PRE-SUBMISSION EVALUATION")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Run all tests
        detection_score = await self.test_scam_detection()
        extraction_score = await self.test_intelligence_extraction()
        authenticity_score = await self.test_persona_authenticity()
        latency_score = await self.test_response_time()
        quality_score = self.test_code_quality()
        
        # Calculate overall score (weighted)
        overall_score = (
            detection_score * 0.25 +      # 25% weight
            extraction_score * 0.25 +     # 25% weight
            authenticity_score * 0.20 +   # 20% weight
            latency_score * 0.20 +        # 20% weight
            quality_score * 0.10          # 10% weight
        )
        
        self.results["overall_score"] = overall_score
        
        # Print final summary
        print("\n" + "="*70)
        print("FINAL EVALUATION SUMMARY")
        print("="*70)
        print(f"Scam Detection Accuracy:    {detection_score:.1f}% (Weight: 25%)")
        print(f"Intelligence Extraction:    {extraction_score:.1f}% (Weight: 25%)")
        print(f"Persona Authenticity:       {authenticity_score:.1f}% (Weight: 20%)")
        print(f"Response Time (Latency):    {latency_score:.1f}% (Weight: 20%)")
        print(f"Code Quality:               {quality_score:.1f}% (Weight: 10%)")
        print("-"*70)
        print(f"OVERALL SCORE:              {overall_score:.1f}%")
        print("="*70)
        
        # Grade
        if overall_score >= 90:
            grade = "A+ (EXCELLENT - Ready for submission)"
        elif overall_score >= 80:
            grade = "A (VERY GOOD - Ready for submission)"
        elif overall_score >= 70:
            grade = "B (GOOD - Minor improvements recommended)"
        elif overall_score >= 60:
            grade = "C (ACCEPTABLE - Some improvements needed)"
        else:
            grade = "D (NEEDS WORK - Significant improvements required)"
        
        print(f"\nFINAL GRADE: {grade}\n")
        
        # Save results
        with open("evaluation_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print("Detailed results saved to: evaluation_results.json\n")
        
        return overall_score

async def main():
    evaluator = Evaluator()
    await evaluator.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
