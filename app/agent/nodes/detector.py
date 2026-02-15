"""
Scam Detector Node.
Analyzes incoming messages to classify as safe/suspected/confirmed scam.
Uses keyword heuristics only (deterministic).
"""
import time
from typing import Dict, Any

from app.agent.state import AgentState
from app.core.rules import (
    CONFIRMED_SCAM_KEYWORDS,
    SUSPECTED_SCAM_KEYWORDS,
    CONFIDENCE_CONFIRMED,
    CONFIDENCE_SUSPECTED,
    CONFIDENCE_SAFE,
)


async def detector_node(state: AgentState) -> Dict[str, Any]:
    """
    Detector node: Analyzes message for scam indicators using keyword heuristics.
    
    Input: current_user_message (string)
    Output: updates scam_level and scam_confidence only
    
    Rules:
    - If message asks for money / UPI / OTP → confirmed (confidence: 0.9)
    - If message contains urgency / KYC / blocked → suspected (confidence: 0.6)
    - Else → safe (confidence: 0.1)
    """
    t_start = time.perf_counter()
    
    message = state["current_user_message"].lower()
    
    result: Dict[str, Any] = {}
    
    # Check for confirmed scam indicators
    matched = False
    for keyword in CONFIRMED_SCAM_KEYWORDS:
        if keyword in message:
            result = {
                "scam_level": "confirmed",
                "scam_confidence": CONFIDENCE_CONFIRMED,
                "is_scam_confirmed": True,
            }
            matched = True
            break
    
    if not matched:
        # Check for suspected scam indicators
        for keyword in SUSPECTED_SCAM_KEYWORDS:
            if keyword in message:
                result = {
                    "scam_level": "suspected",
                    "scam_confidence": CONFIDENCE_SUSPECTED,
                }
                matched = True
                break
    
    if not matched:
        # Default: safe
        result = {
            "scam_level": "safe",
            "scam_confidence": CONFIDENCE_SAFE,
        }
    
    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
    result["timing_log"] = [{"node": "detector", "duration_ms": duration_ms}]
    return result

