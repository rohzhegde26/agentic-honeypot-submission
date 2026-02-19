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
    
    # 1. Letter Swaps (Only if part of a digit sequence)
    # Example: "9 8 O 7" -> "9 8 0 7"
    normalized = text.lower()
    # Replace 'o' with '0' only if it's preceded or followed by a digit or space+digit
    normalized = re.sub(r'(?<=\d\s)o\b|\bo(?=\s\d)|(?<=\d)o|o(?=\d)', '0', normalized)
    # Replace 'l' with '1' similarly
    normalized = re.sub(r'(?<=\d\s)l\b|\bl(?=\s\d)|(?<=\d)l|l(?=\d)', '1', normalized)
    
    # 2. Replace written words with digits
    for word, digit in word_to_digit.items():
        # Use regex to replace whole words only
        normalized = re.sub(fr'\b{word}\b', digit, normalized)
        
    # 3. Mixed Noise Handling (Remove dots, commas, brackets between digits)
    # Example: 9.8(7)6 -> 9876
    # We look for digits separated by 1-2 non-alphanumeric characters or spaces
    noise_pattern = re.compile(r'(?<=\d)[.\s,()\[\]\-_]{1,2}(?=\d)')
    normalized = noise_pattern.sub("", normalized)
    
    # 4. Handle digit strings with spaces (e.g. "9 8 7 6 5 4 3 2 1 0")
    # Matches remaining sequences of digits separated by spaces
    spaced_digit_pattern = re.compile(r'\b\d(?:[\s-]+\d)+\b')
    normalized = spaced_digit_pattern.sub(lambda m: m.group(0).replace(" ", "").replace("-", ""), normalized)
    
    return normalized
