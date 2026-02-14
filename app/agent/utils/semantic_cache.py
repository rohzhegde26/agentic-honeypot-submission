"""
Semantic Cache for Common Scam Openings.
Provides instant responses for frequently seen scam patterns.
"""
from typing import Dict, Optional
import hashlib

# Top 10 common scam opening patterns with pre-cached responses
SCAM_OPENING_CACHE: Dict[str, str] = {
    # UPI/KYC scams
    "account_blocked_kyc": "Oh no! What happened? My account is blocked? I need my pension money for medicine. What should I do sir?",
    "kyc_update_urgent": "KYC update? But I already did this last month... or was it last year? I am confused. Tell me what to do.",
    "upi_verification": "UPI verification? I don't understand these things beta. My grandson usually helps me. What is the problem?",
    
    # OTP scams
    "otp_request": "OTP? You mean the SMS code? But the TV news said never share OTP with anyone. Are you really from the bank?",
    "sms_code_needed": "SMS code? Let me check my phone... wait my glasses... where did I keep them. One minute sir.",
    
    # Prize/lottery scams
    "prize_won": "I won something? Really? But I never entered any lottery. How is this possible? What is your name sir?",
    "cashback_claim": "Cashback? How much? This sounds too good... my neighbor said these are scam calls. Which bank are you from?",
    
    # Job scams
    "work_from_home": "Work from home? At my age? I am 67 years old beta. Are you sure you have the right number?",
    
    # Investment scams
    "investment_opportunity": "Investment? I only have my pension money. I cannot risk it. My wife will get very angry. Who are you?",
    
    # Generic urgent
    "urgent_action": "Urgent? What is so urgent? I am getting tension now. Please explain slowly, I am old person.",
}

def get_cache_key(message: str) -> str:
    """Generate cache key from message by normalizing and hashing."""
    normalized = message.lower().strip()
    # Remove extra whitespace
    normalized = " ".join(normalized.split())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]

def match_scam_pattern(message: str) -> Optional[str]:
    """
    Check if message matches a common scam opening pattern.
    Returns cached response if match found, None otherwise.
    """
    msg_lower = message.lower()
    
    # Pattern matching rules
    if any(k in msg_lower for k in ["account", "block"]) and any(k in msg_lower for k in ["kyc", "update"]):
        return SCAM_OPENING_CACHE["account_blocked_kyc"]
    
    if "kyc" in msg_lower and any(k in msg_lower for k in ["urgent", "immediate", "update"]):
        return SCAM_OPENING_CACHE["kyc_update_urgent"]
    
    if "upi" in msg_lower and any(k in msg_lower for k in ["verify", "verification", "confirm"]):
        return SCAM_OPENING_CACHE["upi_verification"]
    
    if "otp" in msg_lower or "one time password" in msg_lower:
        return SCAM_OPENING_CACHE["otp_request"]
    
    if any(k in msg_lower for k in ["sms", "code"]) and any(k in msg_lower for k in ["send", "share", "enter"]):
        return SCAM_OPENING_CACHE["sms_code_needed"]
    
    if any(k in msg_lower for k in ["won", "winner", "prize", "lottery"]):
        return SCAM_OPENING_CACHE["prize_won"]
    
    if any(k in msg_lower for k in ["cashback", "refund", "reward"]):
        return SCAM_OPENING_CACHE["cashback_claim"]
    
    if "work from home" in msg_lower or ("work" in msg_lower and "home" in msg_lower):
        return SCAM_OPENING_CACHE["work_from_home"]
    
    if any(k in msg_lower for k in ["invest", "profit", "crypto", "bitcoin"]):
        return SCAM_OPENING_CACHE["investment_opportunity"]
    
    if any(k in msg_lower for k in ["urgent", "immediate"]) and any(k in msg_lower for k in ["action", "required", "needed"]):
        return SCAM_OPENING_CACHE["urgent_action"]
    
    return None
