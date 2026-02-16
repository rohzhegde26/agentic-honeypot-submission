import random

def inject_typos(text: str, probability: float = 0.05) -> str:
    """
    Injects realistic typos into a string.
    - Swapping adjacent characters
    - Skipping a character
    - Doubling a character
    - Replacing a character with a neighbor on a QWERTY keyboard (simplified)
    """
    if not text or len(text) < 3:
        return text
        
    words = text.split()
    new_words = []
    
    for word in words:
        if random.random() > probability or len(word) < 4:
            new_words.append(word)
            continue
            
        # Select typo type
        typo_type = random.choice(["swap", "skip", "double"])
        idx = random.randint(1, len(word) - 2)
        
        if typo_type == "swap":
            word_list = list(word)
            word_list[idx], word_list[idx+1] = word_list[idx+1], word_list[idx]
            new_words.append("".join(word_list))
        elif typo_type == "skip":
            new_words.append(word[:idx] + word[idx+1:])
        elif typo_type == "double":
            new_words.append(word[:idx] + word[idx] + word[idx:])
        else:
            new_words.append(word)
            
    return " ".join(new_words)

def apply_elderly_formatting(text: str) -> str:
    """
    Applies common elderly typing quirks:
    - Multiple spaces
    - Ellipsis (...)
    - Random capitalization (rare)
    - Extra punctuation
    """
    if not text:
        return text
        
    # Add extra spaces after sentences
    text = text.replace(". ", ".  ")
    
    # Randomly add ellipsis instead of commas or periods
    if random.random() < 0.3:
        text = text.replace(", ", "... ")
    
    # 5% chance to double up punctuation
    if random.random() < 0.2:
        text = text.replace("?", "??").replace("!", "!!")
        
    return text
