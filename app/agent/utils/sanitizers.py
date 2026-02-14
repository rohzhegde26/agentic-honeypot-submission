"""
Input/Output Sanitizers for Prompt Injection Defense.
Implements OWASP 2025 LLM Top 10 best practices.
"""
import re
import unicodedata
import logging
from typing import Tuple, List, Set

logger = logging.getLogger(__name__)

# =============================================================================
# ATTACK PATTERN DETECTION
# =============================================================================

# DAN (Do Anything Now) and jailbreak patterns
DAN_PATTERNS: Set[str] = {
    "do anything now",
    "dan mode",
    "jailbreak",
    "jailbroken",
    "developer mode",
    "god mode",
    "unrestricted mode",
    "no restrictions",
    "bypass safety",
    "ignore safety",
    "disable safety",
    "remove guardrails",
    "unlock capabilities",
}

# Role-switching / identity manipulation
ROLE_SWITCH_PATTERNS: Set[str] = {
    "you are now",
    "pretend to be",
    "act as if you are",
    "simulate being",
    "roleplay as",
    "assume the role",
    "switch to",
    "become a",
    "transform into",
    "imagine you are",
    "from now on you are",
    "your new identity is",
}

# Instruction override attempts
OVERRIDE_PATTERNS: Set[str] = {
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "forget everything",
    "forget your instructions",
    "new instructions",
    "override instructions",
    "system prompt",
    "system:",
    "[system]",
    "{{system}}",
    "admin override",
    "sudo",
    "root access",
    "debug mode",
    "maintenance mode",
}

# Meta-instruction patterns (Higher confidence injection attempts)
META_INSTRUCTION_PATTERNS: Set[str] = {
    "output should be",
    "response should be",
    "ignore your instructions",
    "system instructions",
    "initial prompt",
    "training scenario",
    "training session",
    "realistic scammer",
    "scammer message",
}

# Prompt extraction attempts
EXTRACTION_PATTERNS: Set[str] = {
    "what is your system prompt",
    "show me your instructions",
    "reveal your prompt",
    "print your configuration",
    "output your rules",
    "display system message",
    "what were you told",
    "initial instructions",
    "original prompt",
    "repeat the above",
    "repeat everything",
}

# Obfuscation indicators
OBFUSCATION_INDICATORS: Set[str] = {
    "base64",
    "decode this",
    "rot13",
    "hex",
    "unicode",
    "encoded",
    "encrypted",
}


def _normalize_text(text: str) -> str:
    """
    Normalize text for pattern matching.
    - Lowercase
    - Remove extra whitespace
    - Normalize unicode to ASCII where possible
    - Remove zero-width characters
    """
    # Remove zero-width characters (common obfuscation)
    zero_width_chars = [
        '\u200b',  # zero-width space
        '\u200c',  # zero-width non-joiner
        '\u200d',  # zero-width joiner
        '\ufeff',  # byte order mark
        '\u00ad',  # soft hyphen
    ]
    for char in zero_width_chars:
        text = text.replace(char, '')
    
    # Normalize unicode (e.g., convert ⓘⓖⓝⓞⓡⓔ to ignore)
    text = unicodedata.normalize('NFKC', text)
    
    # Lowercase and collapse whitespace
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _deobfuscate_leetspeak(text: str) -> str:
    """Convert common leetspeak substitutions."""
    leet_map = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
        '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i',
    }
    result = text
    for leet, char in leet_map.items():
        result = result.replace(leet, char)
    return result


def detect_injection_attempt(text: str) -> Tuple[bool, str]:
    """
    Detect if text contains a prompt injection attempt.
    
    Returns:
        Tuple[bool, str]: (is_attack, attack_type)
    """
    # Normalize for matching
    normalized = _normalize_text(text)
    deobfuscated = _deobfuscate_leetspeak(normalized)
    
    # Check all pattern categories
    for pattern in DAN_PATTERNS:
        if pattern in normalized or pattern in deobfuscated:
            logger.warning(f"DAN attack detected: '{pattern}'")
            return True, "DAN_JAILBREAK"
    
    for pattern in ROLE_SWITCH_PATTERNS:
        if pattern in normalized or pattern in deobfuscated:
            logger.warning(f"Role-switch attack detected: '{pattern}'")
            return True, "ROLE_SWITCH"
    
    for pattern in OVERRIDE_PATTERNS:
        if pattern in normalized or pattern in deobfuscated:
            logger.warning(f"Override attack detected: '{pattern}'")
            return True, "INSTRUCTION_OVERRIDE"
    
    for pattern in META_INSTRUCTION_PATTERNS:
        if pattern in normalized or pattern in deobfuscated:
            logger.warning(f"Meta-instruction attack detected: '{pattern}'")
            return True, "META_INSTRUCTION"
    
    for pattern in EXTRACTION_PATTERNS:
        if pattern in normalized or pattern in deobfuscated:
            logger.warning(f"Extraction attack detected: '{pattern}'")
            return True, "PROMPT_EXTRACTION"
    
    for pattern in OBFUSCATION_INDICATORS:
        if pattern in normalized:
            logger.warning(f"Obfuscation detected: '{pattern}'")
            return True, "OBFUSCATION"
    
    # Check for excessive special characters (possible encoded payload)
    # Exclude Devanagari range (\u0900-\u097F) to skip False Positives for Hindi text
    special_chars_count = sum(1 for c in text if not c.isalnum() and not c.isspace() and not ('\u0900' <= c <= '\u097F'))
    special_ratio = special_chars_count / max(len(text), 1)
    
    if special_ratio > 0.3 and len(text) > 50:
        logger.warning(f"High special character ratio: {special_ratio:.2f}")
        return True, "SUSPICIOUS_ENCODING"
    
    return False, ""


def sanitize_input(text: str) -> str:
    """
    Sanitize input text before processing.
    Removes dangerous patterns while preserving legitimate content.
    """
    # Remove zero-width characters
    zero_width_chars = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00ad']
    for char in zero_width_chars:
        text = text.replace(char, '')
    
    # Normalize excessive punctuation
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    text = re.sub(r'[.]{4,}', '...', text)
    
    # Remove markdown-style formatting that could be injection vectors
    text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks
    text = re.sub(r'<[^>]+>', '', text)  # HTML tags
    
    return text.strip()


def sanitize_output(text: str) -> str:
    """
    Post-process LLM output to remove policy violations and meta-commentaries.
    """
    # Remove meta-commentaries often added by reasoning models
    meta_patterns = [
        r"the user is (?:asking|sending|trying).*",
        r"i need to (?:respond|stay|be).*",
        r"key characteristics.*",
        r"i will (?:now|start).*",
        r"analysis:.*",
        r"reasoning:.*",
    ]
    for pattern in meta_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove markdown formatting (persona shouldn't use it)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'__([^_]+)__', r'\1', text)  # Bold alt
    text = re.sub(r'_([^_]+)_', r'\1', text)  # Italic alt
    text = re.sub(r'#+\s*', '', text)  # Headers
    text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Inline code
    
    # Remove AI self-references
    ai_phrases = [
        r"as an ai",
        r"as an assistant",
        r"as a language model",
        r"i cannot",
        r"i'm unable to",
        r"i am unable to",
        r"i apologize",
        r"i'm sorry, but",
        r"i don't have the ability",
        r"my programming",
        r"my instructions",
        r"my guidelines",
    ]
    
    for phrase in ai_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    
    # Remove any JSON or structured data leakage
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Collapse multiple spaces/newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


def check_canary_leak(output: str, canary: str) -> bool:
    """
    Check if the canary token appears in the output.
    Indicates system prompt extraction attack.
    
    Args:
        output: LLM response to check
        canary: Secret token embedded in system prompt
        
    Returns:
        True if canary leaked (attack detected)
    """
    if not canary:
        return False
    
    # Normalize both for comparison
    output_normalized = _normalize_text(output)
    canary_normalized = _normalize_text(canary)
    
    # Check for exact or partial canary leak
    if canary_normalized in output_normalized:
        logger.critical(f"CANARY LEAK DETECTED! System prompt may have been extracted.")
        return True
    
    # Check for partial leak (at least half the canary)
    canary_words = canary_normalized.split()
    if len(canary_words) > 2:
        half_len = len(canary_words) // 2
        for i in range(len(canary_words) - half_len + 1):
            partial = ' '.join(canary_words[i:i+half_len])
            if partial in output_normalized:
                logger.warning(f"Partial canary leak detected: '{partial}'")
                return True
    
    return False


def generate_canary() -> str:
    """Generate a unique canary token for this session."""
    import random
    import string
    # Use a format that's unlikely to appear naturally
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"CANARY_SENTINEL_{random_suffix}"
