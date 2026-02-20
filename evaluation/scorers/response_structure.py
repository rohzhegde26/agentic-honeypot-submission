"""
Response Structure Scorer — 10 Points.
Black-box: checks presence of required and optional fields.

Rubric:
  sessionId:                     2 pts (Required)
  scamDetected:                  2 pts (Required)
  extractedIntelligence:         2 pts (Required)
  totalMessagesExchanged AND 
    engagementDurationSeconds:   1 pt  (Optional)
  agentNotes:                    1 pt  (Optional)
  scamType:                      1 pt  (Optional)
  confidenceLevel:               1 pt  (Optional)

  Missing REQUIRED fields incur -1 penalty each.
"""
from typing import Dict, Any, List
from evaluation.api_client import APIResponse


def score_response_structure(
    responses: List[APIResponse],
) -> Dict[str, Any]:
    """
    Score response structure based on field presence.
    Checks the FINAL response for all required/optional fields.
    
    Returns:
        Dict with score, max_score, details, and losses.
    """
    max_score = 10
    losses = []

    if not responses:
        return {
            "score": 0,
            "max_score": max_score,
            "details": "No responses received.",
            "losses": [{"points_lost": 10, "reason": "No API responses — could not evaluate response structure."}],
        }

    final = responses[-1]
    raw = final.raw
    score = 0
    breakdown = []

    # ── Required Fields ──

    # sessionId (2 pts, required)
    if raw.get("sessionId"):
        score += 2
        breakdown.append("  ✅ sessionId: +2pts")
    else:
        score -= 1  # penalty for missing required
        losses.append({
            "points_lost": 3,
            "reason": "Missing required field 'sessionId' in response. "
                      "This incurs a -1 penalty plus losing the 2pt field value. "
                      "The API must include sessionId in every response.",
        })
        breakdown.append("  ❌ sessionId: MISSING (required, -1 penalty)")

    # scamDetected (2 pts, required)
    if "scamDetected" in raw:
        score += 2
        breakdown.append(f"  ✅ scamDetected: +2pts (value: {raw['scamDetected']})")
    else:
        score -= 1
        losses.append({
            "points_lost": 3,
            "reason": "Missing required field 'scamDetected' in response. "
                      "This incurs a -1 penalty plus losing the 2pt field value. "
                      "The API must include scamDetected (true/false) in every response.",
        })
        breakdown.append("  ❌ scamDetected: MISSING (required, -1 penalty)")

    # extractedIntelligence (2 pts, required)
    if raw.get("extractedIntelligence") is not None:
        score += 2
        breakdown.append("  ✅ extractedIntelligence: +2pts")
    else:
        score -= 1
        losses.append({
            "points_lost": 3,
            "reason": "Missing required field 'extractedIntelligence' in response. "
                      "This incurs a -1 penalty plus losing the 2pt field value. "
                      "The API must include extractedIntelligence (even if empty) in every response.",
        })
        breakdown.append("  ❌ extractedIntelligence: MISSING (required, -1 penalty)")

    # ── Optional Fields ──

    # totalMessagesExchanged AND engagementDurationSeconds (1 pt)
    has_messages = bool(raw.get("totalMessagesExchanged") or 
                       (raw.get("engagementMetrics", {}) or {}).get("totalMessagesExchanged"))
    has_duration = bool(raw.get("engagementDurationSeconds") or 
                       (raw.get("engagementMetrics", {}) or {}).get("engagementDurationSeconds"))
    if has_messages and has_duration:
        score += 1
        breakdown.append("  ✅ totalMessagesExchanged + engagementDurationSeconds: +1pt")
    else:
        missing = []
        if not has_messages:
            missing.append("totalMessagesExchanged")
        if not has_duration:
            missing.append("engagementDurationSeconds")
        losses.append({
            "points_lost": 1,
            "reason": f"Missing optional field(s): {', '.join(missing)}. "
                      f"Include both totalMessagesExchanged and engagementDurationSeconds for +1pt.",
        })
        breakdown.append(f"  ❌ engagement metrics: MISSING ({', '.join(missing)})")

    # agentNotes (1 pt)
    if raw.get("agentNotes"):
        score += 1
        notes_preview = str(raw["agentNotes"])[:60]
        breakdown.append(f"  ✅ agentNotes: +1pt ('{notes_preview}...')")
    else:
        losses.append({
            "points_lost": 1,
            "reason": "Missing optional field 'agentNotes'. "
                      "Include agent observations or analysis notes for +1pt.",
        })
        breakdown.append("  ❌ agentNotes: MISSING (optional)")

    # scamType (1 pt)
    if raw.get("scamType"):
        score += 1
        breakdown.append(f"  ✅ scamType: +1pt (value: {raw['scamType']})")
    else:
        losses.append({
            "points_lost": 1,
            "reason": "Missing optional field 'scamType'. "
                      "Include the detected scam type (e.g., 'bank_fraud', 'upi_fraud', 'phishing') for +1pt.",
        })
        breakdown.append("  ❌ scamType: MISSING (optional)")

    # confidenceLevel (1 pt)
    if raw.get("confidenceLevel") is not None:
        score += 1
        breakdown.append(f"  ✅ confidenceLevel: +1pt (value: {raw['confidenceLevel']})")
    else:
        losses.append({
            "points_lost": 1,
            "reason": "Missing optional field 'confidenceLevel'. "
                      "Include a confidence score (e.g., 0.0 to 1.0) for +1pt.",
        })
        breakdown.append("  ❌ confidenceLevel: MISSING (optional)")

    # Clamp score to [0, max]
    score = max(0, min(score, max_score))

    details = "Field-by-field breakdown:\n" + "\n".join(breakdown)

    return {
        "score": score,
        "max_score": max_score,
        "details": details,
        "losses": losses,
    }
