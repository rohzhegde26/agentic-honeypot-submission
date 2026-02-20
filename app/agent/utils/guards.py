import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def strip_narrator_leaks(text: str) -> str:
    """
    Strips common AI meta-commentary leaks like "Thinking:", "Action:", "(Thinking)", etc.
    """
    # 1. Patterns like "Thinking: ...", "Action: ...", "Internal Thought: ...", "<thought>...</thought>"
    patterns = [
        r"(?i)^(thinking|action|internal\s+thought|thought|response|understood|okay|ok|noted|instruction)\s*[:.]\s*",
        r"(?i)\(thinking.*?\)",
        r"(?i)\[thinking.*?\]",
        r"(?i)\*thinking.*?\*",
        r"(?i)<think>.*?</think>",
        r"(?i)<thought>.*?</thought>",
        r"(?i)^as\s+an\s+ai\s+.*?\s*,\s*",
        r"(?i)^as\s+(?:a|the|prof|mr|mrs|ms)\s+.*?\s*[:,-]\s*",
        r"(?i)^i\s+will\s+(now\s+)?(talk|respond|message|act)\s+as\s+.*?\s*[:.-]\s*",
        r"(?i)^identity\s*:\s*phone\s*:\s*.*?\s*ifsc\s*:\s*.*?\b",
        r"(?i)^(phase|language|instruction|topic|active|red-flag|checklist)\s*:\s*.*?\n?",
        r"(?i)^under\s*stood\s*sir\s*", 
        r"(?i)^i\s+should\s+.*?\s*[:.-]\s*",
    ]
    
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned).strip()
        
    # 2. Remove any text before the first colon if it looks like narration/labeling
    # E.g. "Response: 'Hello'" or "Ramesh: Hello" or "I will now say: Hello"
    if ":" in cleaned:
        prefixes = ["i will", "now i", "agent", "persona", "response", "reply", "output", "system"]
        # Add common persona name prefixes if they appear with a colon
        # But be careful not to strip legitimate dialogue if the name is used in-character
        if any(p in cleaned.lower() for p in prefixes) or (len(cleaned.split(":")[0]) < 15):
             parts = cleaned.split(":", 1)
             if len(parts) > 1:
                 potential_speech = parts[1].lstrip(" '\"").rstrip(" '\"")
                 if len(potential_speech) > 2:
                     cleaned = potential_speech
                
    return cleaned.strip()

def identity_lock_filter(text: str, fake_details: List[str]) -> str:
    """
    Safety check: ensure the agent doesn't output its OWN secret fake data
    UNLESS it's intended in the protocol. For now, we'll just log it.
    """
    for detail in fake_details:
        if detail in text:
            logger.warning(f"IDENTITY LEAK DETECTED: Agent output its own fake data: {detail}")
            # We don't necessarily strip it yet, as baiting might be intended.
            # But we could replace it with [REDACTED] if needed for score-chasing.
            
    return text
