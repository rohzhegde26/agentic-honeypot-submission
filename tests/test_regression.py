"""
Regression Tests for Callback Behavior.
Ensures callback fires exactly once per confirmed scam session.
"""
import pytest
from unittest.mock import patch

from app.agent.workflow import run_agent
from app.services.callback_service import should_send_callback, send_final_report


class TestCallbackExactlyOnce:
    """Tests to ensure callback fires exactly once."""
    
    @pytest.mark.asyncio
    async def test_callback_fires_for_confirmed_scam(self, session_factory, mock_callback_tracker, mock_send_callback):
        """
        CRITICAL TEST: Callback must fire when:
        1. is_scam_confirmed = True
        2. termination_reason is set
        3. callback_sent = False
        """
        session = session_factory(
            session_id="regression-001",
            is_scam_confirmed=True,
            termination_reason="extracted_success",
            callback_sent=False,
            extracted_intelligence={
                "bankAccounts": [],
                "upiIds": ["scammer@upi"],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": ["urgent", "blocked"],
            },
        )
        
        # Verify should_send_callback returns True
        assert should_send_callback(session) is True
        
        # Send callback via mock
        with patch("app.services.callback_service.send_final_report", mock_send_callback):
            result = await mock_send_callback(session)
            
        # Verify callback was tracked
        assert mock_callback_tracker["count"] == 1
        assert mock_callback_tracker["payloads"][0]["sessionId"] == "regression-001"
        assert mock_callback_tracker["payloads"][0]["scamDetected"] is True

    @pytest.mark.asyncio
    async def test_no_callback_for_safe_messages(self, session_factory):
        """
        CRITICAL TEST: No callback for safe (non-scam) messages.
        """
        session = session_factory(
            session_id="regression-002",
            is_scam_confirmed=False,  # Not a scam
            termination_reason=None,
            callback_sent=False,
        )
        
        # Verify should_send_callback returns False
        assert should_send_callback(session) is False

    @pytest.mark.asyncio
    async def test_no_duplicate_callbacks(self, session_factory, mock_callback_tracker, mock_send_callback):
        """
        CRITICAL TEST: After callback_sent=True, no more callbacks should fire.
        """
        session = session_factory(
            session_id="regression-003",
            is_scam_confirmed=True,
            termination_reason="extracted_success",
            callback_sent=True,  # Already sent!
        )
        
        # Verify should_send_callback returns False (already sent)
        assert should_send_callback(session) is False
        
        # Tracker should still be at 0
        assert mock_callback_tracker["count"] == 0

    @pytest.mark.asyncio
    async def test_no_callback_without_termination_reason(self, session_factory):
        """
        Callback should NOT fire if termination_reason is not set,
        even if scam is confirmed (intel extraction not complete).
        """
        session = session_factory(
            session_id="regression-004",
            is_scam_confirmed=True,
            termination_reason=None,  # Not terminated yet
            callback_sent=False,
        )
        
        # Verify should_send_callback returns False
        assert should_send_callback(session) is False


class TestCallbackPayload:
    """Tests for callback payload format."""
    
    @pytest.mark.asyncio
    async def test_callback_payload_structure(self, session_factory, mock_callback_tracker, mock_send_callback):
        """Verify callback payload contains all required fields."""
        session = session_factory(
            session_id="payload-001",
            is_scam_confirmed=True,
            termination_reason="max_turns",
            callback_sent=False,
            messages=[
                {"sender": "scammer", "text": "Your account is blocked!"},
                {"sender": "agent", "text": "Oh no, what should I do?"},
            ],
            extracted_intelligence={
                "bankAccounts": ["12345678901234"],
                "upiIds": ["scammer@upi"],
                "phishingLinks": ["fake-kyc.com"],
                "phoneNumbers": ["9876543210"],
                "suspiciousKeywords": ["blocked", "urgent"],
            },
        )
        
        await mock_send_callback(session)
        
        payload = mock_callback_tracker["payloads"][0]
        assert "sessionId" in payload
        assert "scamDetected" in payload
        assert "extractedIntelligence" in payload
        assert payload["extractedIntelligence"]["upiIds"] == ["scammer@upi"]
        assert payload["extractedIntelligence"]["bankAccounts"] == ["12345678901234"]

    @pytest.mark.asyncio
    async def test_send_final_report_uses_pdf_schema_and_moves_extra_intel_to_notes(self, session_factory):
        """Verify final callback JSON matches PDF schema and spills extra intel to agentNotes."""
        session = session_factory(
            session_id="payload-002",
            is_scam_confirmed=True,
            termination_reason="extracted_success",
            callback_sent=False,
            messages=[
                {"sender": "scammer", "text": "Share UPI and account details now!"},
                {"sender": "agent", "text": "Please explain what to do."},
            ],
            extracted_intelligence={
                "phoneNumbers": ["9876543210"],
                "bankAccounts": ["12345678901234"],
                "upiIds": ["scammer@upi"],
                "phishingLinks": ["http://fake-link.test"],
                "emailAddresses": ["fraud@mailer.test"],
                "suspiciousKeywords": ["urgent", "blocked"],
                "staffIds": ["STAFF-9"],
            },
        )
        session.agent_notes = "Scammer attempted urgent pressure tactics."

        captured = {}

        class DummyResponse:
            def __init__(self, status_code: int, text: str = "ok"):
                self.status_code = status_code
                self.text = text

        class DummyClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json, headers):
                captured["url"] = url
                captured["json"] = json
                captured["headers"] = headers
                return DummyResponse(200)

        class DummySettings:
            CALLBACK_MAX_RETRIES = 1
            CALLBACK_TIMEOUT = 5
            CALLBACK_URL = "https://callback.local/mock"

        with patch("app.services.callback_service.get_settings", return_value=DummySettings()):
            with patch("app.services.callback_service.httpx.AsyncClient", return_value=DummyClient()):
                ok = await send_final_report(session)

        assert ok is True
        assert captured["url"] == "https://callback.local/mock"
        assert captured["headers"] == {"Content-Type": "application/json"}

        payload = captured["json"]
        assert set(payload.keys()) == {
            "sessionId",
            "scamDetected",
            "totalMessagesExchanged",
            "extractedIntelligence",
            "agentNotes",
        }
        assert set(payload["extractedIntelligence"].keys()) == {
            "phoneNumbers",
            "bankAccounts",
            "upiIds",
            "phishingLinks",
            "emailAddresses",
        }
        assert "suspiciousKeywords" not in payload["extractedIntelligence"]
        assert "staffIds" not in payload["extractedIntelligence"]
        assert "Additional intelligence captured outside callback schema:" in payload["agentNotes"]
        assert "suspiciousKeywords: urgent, blocked" in payload["agentNotes"]
        assert "staffIds: STAFF-9" in payload["agentNotes"]



class TestAgentScamDetection:
    """Integration tests for agent scam detection flow."""
    
    @pytest.mark.asyncio
    async def test_scam_message_detected(self, sample_scam_message, sample_metadata):
        """Test that obvious scam messages are detected."""
        result = await run_agent(
            session_id="detection-001",
            message=sample_scam_message,
            messages_history=[],
            metadata=sample_metadata,
            turn_count=1,
        )
        
        # Should detect as suspected or confirmed scam
        assert result["scam_level"] in ["suspected", "confirmed"]
    
    @pytest.mark.asyncio
    async def test_safe_message_not_flagged(self, sample_safe_message, sample_metadata):
        """Test that harmless messages are not flagged as scam."""
        result = await run_agent(
            session_id="detection-002",
            message=sample_safe_message,
            messages_history=[],
            metadata=sample_metadata,
            turn_count=1,
        )
        
        # Should be safe
        assert result["scam_level"] == "safe"

    @pytest.mark.asyncio
    async def test_extraction_populates_intelligence(self, sample_metadata):
        """Test that scam messages trigger intelligence extraction."""
        message = "Send Rs 500 to verify@paytm or your account 12345678901234 will be frozen!"
        
        result = await run_agent(
            session_id="extraction-001",
            message=message,
            messages_history=[],
            metadata=sample_metadata,
            turn_count=1,
        )
        
        intel = result.get("extracted_intelligence", {})
        
        # Should extract UPI or bank account
        has_intel = (
            len(intel.get("upiIds", [])) > 0 or
            len(intel.get("bankAccounts", [])) > 0
        )
        assert has_intel, f"Expected intelligence extraction, got: {intel}"

    @pytest.mark.asyncio
    async def test_max_turns_does_not_terminate(self, sample_metadata):
        """Test that high turn count does NOT cause termination (intel-based design)."""
        result = await run_agent(
            session_id="max-turns-001",
            message="Hello again",
            messages_history=[],
            metadata=sample_metadata,
            turn_count=9,  # High turn count
        )
        
        # Intel-based design: no max_turns termination
        # Termination only happens on extracted_success
        assert result.get("termination_reason") is None, \
            "Expected no termination (intel-based design, no turn limit)"
