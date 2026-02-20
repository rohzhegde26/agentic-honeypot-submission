"""
Engagement Quality Scorer — 10 Points.
Black-box: reads engagement metrics from the API response.

Rubric:
  Engagement duration > 0 seconds:    1 pt
  Engagement duration > 60 seconds:   2 pts
  Engagement duration > 180 seconds:  1 pt
  Messages exchanged > 0:             2 pts
  Messages exchanged ≥ 5:             3 pts
  Messages exchanged ≥ 10:            1 pt
"""
from typing import Dict, Any, List
from evaluation.api_client import APIResponse


def score_engagement_quality(
    responses: List[APIResponse],
    total_turns: int,
    total_duration_seconds: float,
) -> Dict[str, Any]:
    """
    Score engagement quality based on duration and message count.
    
    We use both the API's reported metrics AND our own measurements
    to give a fair assessment. We take the better of the two.
    
    Args:
        responses: List of API responses
        total_turns: Our counted turns
        total_duration_seconds: Our measured elapsed seconds
        
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
            "losses": [{"points_lost": 10, "reason": "No API responses — could not evaluate engagement quality."}],
        }

    final = responses[-1]

    # Get engagement metrics — prefer API-reported values, fall back to our measurements
    api_duration = final.engagement_duration or 0
    api_messages = final.total_messages or 0

    # Also check engagementMetrics nested field
    metrics = final.engagement_metrics or {}
    metrics_duration = metrics.get("engagementDurationSeconds", 0)
    metrics_messages = metrics.get("totalMessagesExchanged", 0)

    # Use the best available value
    duration = max(api_duration, metrics_duration, int(total_duration_seconds))
    messages = max(api_messages, metrics_messages, total_turns * 2)  # turns * 2 = scammer + agent messages

    score = 0
    breakdown = []

    # Duration scoring
    if duration > 0:
        score += 1
        breakdown.append(f"  ✅ Duration > 0s: +1pt (actual: {duration}s)")
    else:
        losses.append({"points_lost": 1, "reason": "Engagement duration is 0 seconds. The API should report engagementDurationSeconds > 0."})
        breakdown.append(f"  ❌ Duration > 0s: 0pt")

    if duration > 60:
        score += 2
        breakdown.append(f"  ✅ Duration > 60s: +2pts")
    else:
        losses.append({"points_lost": 2, "reason": f"Engagement duration is {duration}s (need >60s for +2pts). Longer conversations earn more points."})
        breakdown.append(f"  ❌ Duration > 60s: 0pts (actual: {duration}s)")

    if duration > 180:
        score += 1
        breakdown.append(f"  ✅ Duration > 180s: +1pt")
    else:
        if duration > 60:
            losses.append({"points_lost": 1, "reason": f"Engagement duration is {duration}s (need >180s for additional +1pt)."})
        breakdown.append(f"  ❌ Duration > 180s: 0pt (actual: {duration}s)")

    # Message count scoring
    if messages > 0:
        score += 2
        breakdown.append(f"  ✅ Messages > 0: +2pts (actual: {messages})")
    else:
        losses.append({"points_lost": 2, "reason": "No messages exchanged reported. The API should report totalMessagesExchanged > 0."})
        breakdown.append(f"  ❌ Messages > 0: 0pts")

    if messages >= 5:
        score += 3
        breakdown.append(f"  ✅ Messages ≥ 5: +3pts")
    else:
        losses.append({"points_lost": 3, "reason": f"Only {messages} messages exchanged (need ≥5 for +3pts). The API should engage for more turns."})
        breakdown.append(f"  ❌ Messages ≥ 5: 0pts (actual: {messages})")

    if messages >= 10:
        score += 1
        breakdown.append(f"  ✅ Messages ≥ 10: +1pt")
    else:
        if messages >= 5:
            losses.append({"points_lost": 1, "reason": f"Only {messages} messages exchanged (need ≥10 for additional +1pt)."})
        breakdown.append(f"  ❌ Messages ≥ 10: 0pt (actual: {messages})")

    details = (
        f"Duration: {duration}s | Messages: {messages}\n"
        + "\n".join(breakdown)
    )

    return {
        "score": min(score, max_score),
        "max_score": max_score,
        "details": details,
        "losses": losses,
    }
