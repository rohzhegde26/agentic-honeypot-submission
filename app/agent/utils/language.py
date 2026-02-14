def is_hindi(text: str) -> bool:
    """Detect if text contains Hindi characters (Devanagari script)."""
    if not text:
        return False
    # Devanagari range: \u0900 to \u097F
    for char in text:
        if '\u0900' <= char <= '\u097F':
            return True
    return False
