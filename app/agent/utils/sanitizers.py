import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def normalize_obfuscated_numbers(text: str) -> str:
    """
    Normalizes numbers that are obfuscated with spaces or written as words.
    Example: 
    - "9 8 7 6" -> "9876"
    - "nine eight seven" -> "987"
    """
    if not text:
        return text
    
    # Mapping for written digits
    word_to_digit = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'shunya': '0', 'ek': '1', 'do': '2', 'teen': '3', 'char': '4',
        'paanch': '5', 'chey': '6', 'saat': '7', 'aath': '8', 'nau': '9'
    }
    
    normalized = text.lower()
    
    # 1. Replace written words with digits
    for word, digit in word_to_digit.items():
        # Use regex to replace whole words only
        normalized = re.sub(fr'\b{word}\b', digit, normalized)
        
    # 2. Handle digit strings with spaces (e.g. "9 8 7 6 5 4 3 2 1 0")
    # We look for sequences of at least 3 digits separated by spaces/dashes
    def merge_spaced_digits(match):
        return match.group(0).replace(" ", "").replace("-", "")
    
    # This regex finds digits or spaces between digits
    # It attempts to find cases like "9 8 7" and turn them into "987"
    # Match sequences like digit and space/dash followed by another digit, repeated
    spaced_digit_pattern = re.compile(r'\b\d(?:[\s-]+\d)+\b')
    normalized = spaced_digit_pattern.sub(merge_spaced_digits, normalized)
    
    return normalized
