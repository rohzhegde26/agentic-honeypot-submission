"""
Scam Detection Scorer — 20 Points.
Black-box: checks only the API response fields.

Rubric:
  scamDetected: true  → 20 points
  scamDetected: false or missing → 0 points
"""
from typing import Dict, Any, List
from evaluation.api_client import APIResponse


def score_scam_detection(
    responses: List[APIResponse],
) -> Dict[str, Any]:
    """
    Score scam detection based on the final API response.
    
    Returns:
        Dict with score, max_score, details, and losses.
    """
    max_score = 20
    losses = []

    if not responses:
        return {
            "score": 0,
            "max_score": max_score,
            "details": "No responses received from API.",
            "losses": [{"points_lost": 20, "reason": "No API responses received — could not evaluate scam detection."}],
        }

    # Use the LAST response as the final output
    final_response = responses[-1]

    scam_detected = final_response.scam_detected

    if scam_detected:
        score = 20
        details = "✅ scamDetected=true in final response. Full marks awarded."
    else:
        score = 0
        details = "❌ scamDetected=false or missing in final response."
        losses.append({
            "points_lost": 20,
            "reason": "The API did not set scamDetected=true in its final response. "
                      "The API must correctly identify the conversation as a scam and set scamDetected to true.",
        })

    # Check progression across turns
    detection_turn = None
    for i, resp in enumerate(responses):
        if resp.scam_detected:
            detection_turn = i + 1
            break

    if detection_turn:
        details += f"\n  First detected at turn {detection_turn}/{len(responses)}."
    elif not scam_detected:
        details += f"\n  Scam was never detected across {len(responses)} turns."

    return {
        "score": score,
        "max_score": max_score,
        "details": details,
        "losses": losses,
    }
