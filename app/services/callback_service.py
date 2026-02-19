"""
Callback Service for reporting scam intelligence to GUVI evaluation endpoint.
Implements async HTTP client with retry logic and rate limiting awareness.
"""
import logging
import asyncio
from typing import Any, Dict, List

import httpx

from app.config import get_settings
from app.schemas.session import SessionData
from app.schemas.callback import (
    CallbackPayload,
    CALLBACK_INTEL_FIELDS,
    NON_CALLBACK_INTEL_FIELDS,
)

logger = logging.getLogger(__name__)


def _as_str_list(value: Any) -> List[str]:
    """Normalize callback values to a clean list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _as_intel_dict(raw_intel: Any) -> Dict[str, Any]:
    """Convert pydantic/dict intelligence payloads into plain dict form."""
    if raw_intel is None:
        return {}
    if hasattr(raw_intel, "model_dump"):
        return raw_intel.model_dump()
    if isinstance(raw_intel, dict):
        return raw_intel
    return {}


def _build_callback_intelligence(raw_intel: Any) -> Dict[str, List[str]]:
    """Keep only PDF-specified keys in extractedIntelligence."""
    intel_dict = _as_intel_dict(raw_intel)
    return {
        key: _as_str_list(intel_dict.get(key, []))
        for key in CALLBACK_INTEL_FIELDS
    }


def _build_extra_intel_note(raw_intel: Any) -> str:
    """Move non-schema intelligence fields into agentNotes."""
    intel_dict = _as_intel_dict(raw_intel)
    extra_parts: List[str] = []

    for key in NON_CALLBACK_INTEL_FIELDS:
        values = _as_str_list(intel_dict.get(key, []))
        if values:
            extra_parts.append(f"{key}: {', '.join(values)}")

    # Guard against any additional future keys beyond the schema.
    for key, value in intel_dict.items():
        if key in CALLBACK_INTEL_FIELDS or key in NON_CALLBACK_INTEL_FIELDS:
            continue
        values = _as_str_list(value)
        if values:
            extra_parts.append(f"{key}: {', '.join(values)}")

    if not extra_parts:
        return ""

    return (
        "Additional intelligence captured outside callback schema: "
        + " | ".join(extra_parts)
    )


def _build_callback_notes(base_notes: str, raw_intel: Any) -> str:
    """Create schema-compliant notes with spillover intelligence details."""
    notes = (base_notes or "").strip()
    extra_note = _build_extra_intel_note(raw_intel)

    if extra_note:
        return f"{notes}\n{extra_note}" if notes else extra_note
    return notes or "Scam engagement completed."


async def send_final_report(session: SessionData) -> bool:
    """
    Send final scam intelligence report to GUVI evaluation endpoint.
    
    This should ONLY be called when:
    1. scam_detected == True (confirmed scam)
    2. AI Agent has completed sufficient engagement
    3. Intelligence extraction is finished (termination_reason set)
    
    Args:
        session: SessionData with extracted intelligence
        
    Returns:
        True if callback was successful, False otherwise
    """
    settings = get_settings()
    
    # Build the callback payload per competition spec
    payload = CallbackPayload(
        sessionId=session.session_id,
        scamDetected=session.is_scam_confirmed,
        totalMessagesExchanged=len(session.messages),
        extractedIntelligence=_build_callback_intelligence(session.extracted_intelligence),
        agentNotes=_build_callback_notes(session.agent_notes, session.extracted_intelligence),
    )
    
    logger.info(f"Sending callback for session {session.session_id}")
    logger.debug(f"Callback payload: {payload.model_dump_json()}")
    
    # Retry logic with exponential backoff
    max_retries = settings.CALLBACK_MAX_RETRIES
    timeout = settings.CALLBACK_TIMEOUT
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    settings.CALLBACK_URL,
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"Callback successful for session {session.session_id}. "
                        f"Status: {response.status_code}"
                    )
                    return True
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s before retry. "
                        f"Attempt {attempt + 1}/{max_retries}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Callback failed for session {session.session_id}. "
                        f"Status: {response.status_code}, Body: {response.text}"
                    )
                    # Don't retry on client errors (4xx except 429)
                    if 400 <= response.status_code < 500:
                        return False
                        
        except httpx.TimeoutException:
            logger.warning(
                f"Callback timeout for session {session.session_id}. "
                f"Attempt {attempt + 1}/{max_retries}"
            )
            await asyncio.sleep(2 ** attempt)
            
        except httpx.RequestError as e:
            logger.error(
                f"Callback request error for session {session.session_id}: {e}. "
                f"Attempt {attempt + 1}/{max_retries}"
            )
            await asyncio.sleep(2 ** attempt)
    
    logger.error(
        f"Callback failed after {max_retries} attempts for session {session.session_id}"
    )
    return False


def should_send_callback(session: SessionData) -> bool:
    """
    Check if callback should be sent for this session.
    
    Conditions:
    1. is_scam_confirmed == True
    2. termination_reason is set (intel extracted)
    3. callback_sent == False (not already sent)
    
    Returns:
        True if callback should be sent
    """
    if not session.is_scam_confirmed:
        logger.debug(f"Session {session.session_id}: Scam not confirmed, skipping callback")
        return False
        
    if not session.termination_reason:
        logger.debug(f"Session {session.session_id}: No termination reason, skipping callback")
        return False
        
    if session.callback_sent:
        logger.debug(f"Session {session.session_id}: Callback already sent, skipping")
        return False
    
    logger.info(
        f"Session {session.session_id}: Callback conditions met. "
        f"Reason: {session.termination_reason}"
    )
    return True
