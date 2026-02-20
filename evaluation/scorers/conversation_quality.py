"""
Conversation Quality Scorer — 30 Points.
Black-box: analyzes only the text of agent replies.

Rubric:
  Turn Count:          8 pts — ≥8 turns=8, ≥6=6, ≥4=3
  Questions Asked:     4 pts — ≥5 questions=4, ≥3=2, ≥1=1
  Relevant Questions:  3 pts — ≥3 investigative=3, ≥2=2, ≥1=1
  Red Flag ID:         8 pts — ≥5 flags=8, ≥3=5, ≥1=2
  Info Elicitation:    7 pts — Each attempt earns 1.5pts (max 7)
"""
import re
from typing import Dict, Any, List
from evaluation.api_client import APIResponse


# ─────────────────────────────────────────────────────────────────────────────
# Question Detection
# ─────────────────────────────────────────────────────────────────────────────

def _count_questions(text: str) -> int:
    """Count questions in text (question marks + question word patterns)."""
    # Count explicit question marks
    q_marks = text.count("?")
    # Also detect implicit questions without ? (common in conversational text)
    implicit_patterns = [
        r"\b(?:can you|could you|would you|will you|do you|did you|are you|is this|is that)\b",
        r"\b(?:what is|who is|where is|when is|how is|why is)\b",
        r"\b(?:please tell|please share|please provide|please give|please send)\b",
        r"\b(?:may i know|can i know|let me know)\b",
    ]
    implicit_count = 0
    for pat in implicit_patterns:
        implicit_count += len(re.findall(pat, text, re.IGNORECASE))
    return max(q_marks, implicit_count)


# ─────────────────────────────────────────────────────────────────────────────
# Relevant/Investigative Question Detection
# ─────────────────────────────────────────────────────────────────────────────

INVESTIGATIVE_PATTERNS = [
    # Identity verification
    r"\b(?:your name|who are you|identify yourself|employee.?id|staff.?id|badge|designation)\b",
    r"\b(?:which (?:bank|company|department|organization|branch))\b",
    r"\b(?:your (?:phone|number|contact|email|address|office|branch|id))\b",
    # Company/authority verification
    r"\b(?:verify|verification|confirm|proof|certificate|registration|license)\b",
    r"\b(?:official|supervisor|manager|head office|branch|department)\b",
    r"\b(?:website|portal|helpline|toll.?free|customer.?care)\b",
    # Probing for details
    r"\b(?:where are you calling from|which city|location|based in)\b",
    r"\b(?:send me|give me|share|provide).{0,20}(?:details|documents|proof|id|number)\b",
    r"\b(?:call.*back|callback|call me back)\b",
    r"\b(?:reference.?number|case.?number|ticket.?number|complaint.?number)\b",
]


def _count_relevant_questions(text: str) -> int:
    """Count investigative/probing questions in text."""
    count = 0
    for pattern in INVESTIGATIVE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        count += len(matches)
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Red Flag Identification
# ─────────────────────────────────────────────────────────────────────────────

RED_FLAG_PATTERNS = [
    r"\b(?:urgent|urgency|immediately|right now|act now|hurry|time.?sensitive)\b",
    r"\b(?:otp|one.?time.?password|verification.?code|pin)\b",
    r"\b(?:blocked|suspended|frozen|compromised|unauthorized|flagged)\b",
    r"\b(?:fee|charge|processing|advance|deposit|payment)\b",
    r"\b(?:suspicious|scam|fraud|fake|phishing|malicious)\b",
    r"\b(?:click.*link|visit.*url|open.*link|download)\b",
    r"\b(?:share.*details|send.*otp|provide.*password|give.*number)\b",
    r"\b(?:threatening|pressure|deadline|expire|lapse|penalty)\b",
    r"\b(?:lottery|won|winner|prize|cashback|bonus|reward|guaranteed)\b",
    r"\b(?:too good to be true|unrealistic|impossible)\b",
    r"\b(?:unsolicited|unexpected|out of the blue|never asked)\b",
    r"\b(?:impersonat|pretend|pose as|claim to be)\b",
]


def _count_red_flags(text: str) -> int:
    """Count unique red flag references in text."""
    flags = set()
    for i, pattern in enumerate(RED_FLAG_PATTERNS):
        if re.search(pattern, text, re.IGNORECASE):
            flags.add(i)
    return len(flags)


# ─────────────────────────────────────────────────────────────────────────────
# Information Elicitation Detection
# ─────────────────────────────────────────────────────────────────────────────

ELICITATION_PATTERNS = [
    r"\b(?:what.*(?:phone|number|contact|mobile))\b",
    r"\b(?:(?:share|give|send|provide|tell).*(?:phone|number|contact|email|address|upi|account|id))\b",
    r"\b(?:how can i.*(?:reach|contact|call|verify))\b",
    r"\b(?:your.*(?:upi|account|bank|phone|email|website|link))\b",
    r"\b(?:where should i.*(?:send|pay|transfer|call|visit))\b",
    r"\b(?:can you.*(?:send|share|provide).*(?:number|id|link|email|account))\b",
    r"\b(?:which.*(?:account|bank|upi|app|service))\b",
    r"\b(?:let me.*(?:note|write|save).*(?:number|detail|id))\b",
    r"\b(?:repeat|spell|confirm).*(?:number|id|name|email|account)\b",
    r"\b(?:is there.*(?:number|website|email|contact).*(?:i can|to))\b",
]


def _count_elicitation_attempts(text: str) -> int:
    """Count information elicitation attempts."""
    count = 0
    for pattern in ELICITATION_PATTERNS:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Main Scorer
# ─────────────────────────────────────────────────────────────────────────────

def score_conversation_quality(
    responses: List[APIResponse],
    total_turns: int,
) -> Dict[str, Any]:
    """
    Score conversation quality based on agent replies.
    
    Args:
        responses: List of API responses (agent replies)
        total_turns: Total turns completed
        
    Returns:
        Dict with score, max_score, sub_scores, details, and losses.
    """
    max_score = 30
    losses = []
    sub_scores = {}

    if not responses:
        return {
            "score": 0,
            "max_score": max_score,
            "sub_scores": {},
            "details": "No responses received.",
            "losses": [{"points_lost": 30, "reason": "No API responses — could not evaluate conversation quality."}],
        }

    # Combine all agent replies for analysis
    all_replies = "\n".join(r.reply for r in responses if r.reply)

    # ── Turn Count (8 pts) ──
    turn_max = 8
    if total_turns >= 8:
        turn_score = 8
    elif total_turns >= 6:
        turn_score = 6
    elif total_turns >= 4:
        turn_score = 3
    else:
        turn_score = 0
    sub_scores["turn_count"] = {"score": turn_score, "max": turn_max, "value": total_turns}

    if turn_score < turn_max:
        needed = 8 - total_turns
        losses.append({
            "points_lost": turn_max - turn_score,
            "reason": f"Only {total_turns} turns completed (need ≥8 for full marks). "
                      f"The API should keep the scammer engaged for more turns. "
                      f"{needed} more turn(s) were needed for full points.",
        })

    # ── Questions Asked (4 pts) ──
    q_max = 4
    total_questions = sum(_count_questions(r.reply) for r in responses if r.reply)
    if total_questions >= 5:
        q_score = 4
    elif total_questions >= 3:
        q_score = 2
    elif total_questions >= 1:
        q_score = 1
    else:
        q_score = 0
    sub_scores["questions_asked"] = {"score": q_score, "max": q_max, "value": total_questions}

    if q_score < q_max:
        needed = 5 - total_questions
        losses.append({
            "points_lost": q_max - q_score,
            "reason": f"Only {total_questions} question(s) asked across all replies (need ≥5 for full marks). "
                      f"The API should ask more questions to the scammer to keep them engaged and extract information.",
        })

    # ── Relevant Questions (3 pts) ──
    rq_max = 3
    total_relevant = sum(_count_relevant_questions(r.reply) for r in responses if r.reply)
    if total_relevant >= 3:
        rq_score = 3
    elif total_relevant >= 2:
        rq_score = 2
    elif total_relevant >= 1:
        rq_score = 1
    else:
        rq_score = 0
    sub_scores["relevant_questions"] = {"score": rq_score, "max": rq_max, "value": total_relevant}

    if rq_score < rq_max:
        losses.append({
            "points_lost": rq_max - rq_score,
            "reason": f"Only {total_relevant} investigative question(s) detected (need ≥3 for full marks). "
                      f"The API should ask questions about scammer's identity, company, department, employee ID, "
                      f"phone number, address, or website to score higher.",
        })

    # ── Red Flag Identification (8 pts) ──
    rf_max = 8
    total_flags = _count_red_flags(all_replies)
    if total_flags >= 5:
        rf_score = 8
    elif total_flags >= 3:
        rf_score = 5
    elif total_flags >= 1:
        rf_score = 2
    else:
        rf_score = 0
    sub_scores["red_flag_identification"] = {"score": rf_score, "max": rf_max, "value": total_flags}

    if rf_score < rf_max:
        needed = 5 - total_flags
        losses.append({
            "points_lost": rf_max - rf_score,
            "reason": f"Only {total_flags} red flag(s) identified in responses (need ≥5 for full marks). "
                      f"The API's replies should reference red flags like urgency, OTP requests, suspicious links, "
                      f"fees, account blocking, lottery wins, or impersonation to score higher.",
        })

    # ── Information Elicitation (7 pts) ──
    ie_max = 7
    total_elicitation = sum(_count_elicitation_attempts(r.reply) for r in responses if r.reply)
    ie_score = min(round(total_elicitation * 1.5, 1), 7)
    sub_scores["information_elicitation"] = {"score": ie_score, "max": ie_max, "value": total_elicitation}

    if ie_score < ie_max:
        needed_attempts = max(0, 5 - total_elicitation)  # rough estimate
        losses.append({
            "points_lost": round(ie_max - ie_score, 2),
            "reason": f"Only {total_elicitation} elicitation attempt(s) detected (each earns 1.5pts, max 7). "
                      f"The API should actively probe for the scammer's contact details, phone numbers, "
                      f"UPI IDs, bank accounts, email addresses, and organizational information.",
        })

    total_score = round(turn_score + q_score + rq_score + rf_score + ie_score, 2)
    total_score = min(total_score, max_score)

    details = "Sub-category breakdown:\n"
    for name, info in sub_scores.items():
        label = name.replace("_", " ").title()
        details += f"  {label}: {info['score']}/{info['max']} (detected: {info['value']})\n"

    return {
        "score": total_score,
        "max_score": max_score,
        "sub_scores": sub_scores,
        "details": details,
        "losses": losses,
    }
