def is_hindi(text: str) -> bool:
    """Detect if text contains any major Indian scripts (Devanagari, Bengali, Tamil, etc.)."""
    if not text:
        return False
        
    # Unicode ranges for major Indian scripts
    ranges = [
        ('\u0900', '\u097F'),  # Devanagari (Hindi, Marathi, etc.)
        ('\u0980', '\u09FF'),  # Bengali / Assamese
        ('\u0A00', '\u0A7F'),  # Gurmukhi (Punjabi)
        ('\u0A80', '\u0AFF'),  # Gujarati
        ('\u0B00', '\u0B7F'),  # Oriya
        ('\u0B80', '\u0BFF'),  # Tamil
        ('\u0C00', '\u0C7F'),  # Telugu
        ('\u0C80', '\u0CFF'),  # Kannada
        ('\u0D00', '\u0D7F'),  # Malayalam
    ]
    
    for char in text:
        for start, end in ranges:
            if start <= char <= end:
                return True
    return False
