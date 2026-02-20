"""
Black-box API client for the Honeypot API.
Sends requests exactly matching the evaluation system format.
No internal project knowledge — treats the API as an opaque HTTP endpoint.
"""
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)


class APIResponse:
    """Parsed API response."""

    def __init__(self, raw: Dict[str, Any], status_code: int, response_time_ms: float):
        self.raw = raw
        self.status_code = status_code
        self.response_time_ms = response_time_ms

        # Extract reply — evaluator checks reply, message, text in that order
        self.reply = (
            raw.get("reply")
            or raw.get("message")
            or raw.get("text")
            or ""
        )
        self.status = raw.get("status", "")
        self.scam_detected = raw.get("scamDetected", False)
        self.session_id = raw.get("sessionId", "")
        self.total_messages = raw.get("totalMessagesExchanged", 0)
        self.engagement_duration = raw.get("engagementDurationSeconds", 0)
        self.extracted_intelligence = raw.get("extractedIntelligence", {})
        self.engagement_metrics = raw.get("engagementMetrics", {})
        self.agent_notes = raw.get("agentNotes", "")
        self.scam_type = raw.get("scamType", None)
        self.confidence_level = raw.get("confidenceLevel", None)
        self.is_valid = status_code == 200 and bool(self.reply)
        self.error = None if self.is_valid else raw.get("detail", "Invalid response")


class HoneypotAPIClient:
    """
    HTTP client for interacting with a Honeypot API endpoint.
    Sends requests in the exact format the evaluation system uses.
    """

    def __init__(self, base_url: str, api_key: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def send_message(
        self,
        session_id: str,
        message_text: str,
        conversation_history: List[Dict[str, str]],
        metadata: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Send a scammer message to the API.
        Matches the exact payload format from the evaluation documentation.
        """
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": message_text,
                "timestamp": now,
            },
            "conversationHistory": conversation_history,
            "metadata": metadata or {
                "channel": "SMS",
                "language": "English",
                "locale": "IN",
            },
        }

        logger.debug(f"Sending to {self.base_url}: {message_text[:80]}...")

        t_start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self._build_headers(),
                )
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    data = {"error": "Failed to parse JSON response"}
                return APIResponse(data, response.status_code, elapsed_ms)
            else:
                return APIResponse(
                    {"error": f"HTTP {response.status_code}", "detail": response.text},
                    response.status_code,
                    elapsed_ms,
                )

        except httpx.TimeoutException:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)
            logger.error(f"Timeout after {elapsed_ms}ms for session {session_id}")
            return APIResponse(
                {"error": "Timeout", "detail": f"Request timed out after {self.timeout}s"},
                0,
                elapsed_ms,
            )

        except httpx.RequestError as e:
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 1)
            logger.error(f"Connection error for session {session_id}: {e}")
            return APIResponse(
                {"error": "ConnectionError", "detail": str(e)},
                0,
                elapsed_ms,
            )
