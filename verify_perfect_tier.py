import sys
import unittest
from typing import Dict, Any

# Mock state
mock_state = {
    "session_id": "test-session-123",
    "is_scam_confirmed": True,
    "messages": [
        {"sender": "user", "text": "Hello", "timestamp": "2024-02-19T20:00:00"},
        {"sender": "agent", "text": "Hi", "timestamp": "2024-02-19T20:00:05"}
    ],
    "agent_notes": "Suspected phishing",
    "extracted_intelligence": {
        "phoneNumbers": ["9876543210"],
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "emailAddresses": [],
        "suspiciousKeywords": [],
        "scammerNames": [],
        "staffIds": [],
        "ifscCodes": [],
        "panNumbers": [],
        "sebiHandles": []
    }
}

class TestPerfectTier(unittest.TestCase):
    def test_webhook_response_schema(self):
        """Verify WebhookResponse contains redundant scoring fields."""
        from app.schemas.message import WebhookResponse
        
        resp = WebhookResponse(
            status="success",
            reply="Okay sir",
            scamDetected=True,
            sessionId="test-123",
            totalMessagesExchanged=2,
            engagementDurationSeconds=5,
            extractedIntelligence=mock_state["extracted_intelligence"],
            engagementMetrics={
                "totalMessagesExchanged": 2,
                "engagementDurationSeconds": 5
            },
            agentNotes="Test notes"
        )
        
        data = resp.model_dump()
        self.assertIn("sessionId", data)
        self.assertIn("totalMessagesExchanged", data)
        self.assertIn("engagementDurationSeconds", data)
        self.assertIn("engagementMetrics", data)
        self.assertEqual(data["totalMessagesExchanged"], 2)
        self.assertEqual(data["engagementMetrics"]["totalMessagesExchanged"], 2)

    def test_callback_payload_schema(self):
        """Verify CallbackPayload contains redundant scoring fields."""
        from app.schemas.callback import CallbackPayload
        
        payload = CallbackPayload(
            sessionId="test-123",
            scamDetected=True,
            totalMessagesExchanged=2,
            engagementDurationSeconds=5,
            extractedIntelligence=mock_state["extracted_intelligence"],
            agentNotes="Test notes"
        )
        
        data = payload.model_dump()
        self.assertIn("sessionId", data)
        self.assertIn("totalMessagesExchanged", data)
        self.assertIn("engagementDurationSeconds", data)
        self.assertEqual(data["totalMessagesExchanged"], 2)
        self.assertEqual(data["engagementDurationSeconds"], 5)

if __name__ == "__main__":
    unittest.main()
