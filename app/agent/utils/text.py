import random
import re

def inject_typos(text: str, probability: float = 0.05) -> str:
    """
    Injects realistic typing errors by swapping adjacent characters.
    """
    if len(text) < 2:
        return text
        
    chars = list(text)
    exclude_words = ["sir", "please", "confused", "plese"]
    
    # Simple check: if a word is in exclude_words, don't mess with it
    words = text.split()
    processed_words = []
    
    for word in words:
        if word.lower().strip(".,!?") in exclude_words:
            processed_words.append(word)
        else:
            if len(word) > 2 and random.random() < probability:
                # Basic typo: swap two chars in the word
                idx = random.randint(0, len(word) - 2)
                w_list = list(word)
                w_list[idx], w_list[idx+1] = w_list[idx+1], w_list[idx]
                processed_words.append("".join(w_list))
            else:
                processed_words.append(word)
                
    return " ".join(processed_words)

def apply_elderly_formatting(text: str) -> str:
    """
    Applies common 'elderly tech user' formatting patterns:
    - Double spaces after sentences.
    - Frequent use of ellipsis (...).
    - Lowercase start of sentences occasionally.
    """
    # 1. Double spaces after periods
    text = text.replace(". ", ".  ")
    
    # 2. Add ellipsis to the end of some sentences
    sentences = re.split('([.!?])', text)
    processed_sentences = []
    
    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i]
        punctuation = sentences[i+1]
        
        # 5% chance to turn period into ellipsis (reduced from 30% for realism)
        if punctuation == "." and random.random() < 0.05:
            punctuation = "..."
            
        processed_sentences.append(sentence + punctuation)
        
    if len(sentences) % 2 != 0:
        processed_sentences.append(sentences[-1])
        
    text = "".join(processed_sentences)
    
    # 3. Occasional lowercase at start (simulating slow typing)
    if text and random.random() < 0.2:
        text = text[0].lower() + text[1:]
        
    return text.strip()
