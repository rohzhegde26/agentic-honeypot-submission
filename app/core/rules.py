"""
Centralized Rules Configuration.
All regex patterns, keywords, and system prompts are defined here.
This module acts as a single source of truth for agent logic.
"""
import re
from typing import List, Pattern


# =============================================================================
# DETECTION RULES
# =============================================================================

# Keywords that indicate a CONFIRMED scam (money/UPI/OTP requests)
CONFIRMED_SCAM_KEYWORDS: List[str] = [
    "send money",
    "transfer money",
    "pay now",
    "upi",
    "otp",
    "one time password",
    "send otp",
    "share otp",
    "enter otp",
    "pin",
    "send pin",
    "share pin",
    "cvv",
    "card number",
    "bank transfer",
    "paytm",
    "gpay",
    "phonepe",
    "google pay",
    "bhim",
]

# Keywords that indicate a SUSPECTED scam (urgency/KYC/blocked)
SUSPECTED_SCAM_KEYWORDS: List[str] = [
    "urgent",
    "urgently",
    "immediately",
    "kyc",
    "blocked",
    "suspended",
    "frozen",
    "verify",
    "verification",
    "expire",
    "expiring",
    "legal action",
    "police",
    "arrest",
    "deadline",
    "last chance",
    "account will be",
    "turant",
    "abhi",
    "jaldi",
    "loan",
    "block",
    "बन्द",
    "बंद",
    "ब्लॉक",
    "केवाईसी",
    "बंद हो गया",
    "अपडेट",
    "वेरिफाई",
    "अकाउंट",
    "खाता",
    "नमस्ते",
    "हेलो",
    "approved",
    "refund",
    "cashback",
    "won",
    "lottery",
    "prize",
    "job",
    "hiring",
    "vacancy",
    "work from home",
    "investment",
    "profit",
    "crypto",
    "bitcoin",
    "gift",
    "customs",
    "apk",
    "install",
    "app",
    "investment",
    "crypto",
    "bitcoin",
    "trading",
    "double",
    "profit",
    "signals",
    "hiring",
    "job",
    "salary",
    "work from home",
    "telegram",
    "task",
    "rating",
    "hospital",
    "accident",
    "emergency",
    "stuck",
    "help",
    "won",
    "prize",
    "lucky",
    "gift",
    "claim",
]

# Scam Type Classification Constants
SCAM_TYPE_BANK = "bank_fraud"
SCAM_TYPE_UPI = "upi_fraud"
SCAM_TYPE_PHISHING = "phishing"
SCAM_TYPE_JOB = "job/recruitment_scam"
SCAM_TYPE_INVESTMENT = "investment/crypto_fraud"
SCAM_TYPE_EMERGENCY = "emergency/emotional_social_engineering"
SCAM_TYPE_UNKNOWN = "unknown"

# Mapping of keywords to scam types for classification
SCAM_TYPE_KEYWORDS = {
    SCAM_TYPE_BANK: ["bank", "sbi", "account", "blocked", "kyc", "card", "atm", "branch"],
    SCAM_TYPE_UPI: ["upi", "paytm", "gpay", "phonepe", "cashback", "wallet", "qr code", "claim"],
    SCAM_TYPE_PHISHING: ["link", "click", "url", "website", "http", "www", "portal", "login", "update"],
    SCAM_TYPE_JOB: ["job", "salary", "work from home", "hiring", "vacancy", "task", "rating", "telegram"],
    SCAM_TYPE_INVESTMENT: ["investment", "crypto", "bitcoin", "trade", "profit", "trading", "signal"],
    SCAM_TYPE_EMERGENCY: ["hospital", "accident", "emergency", "stuck", "help", "police", "arrest"],
}



# =============================================================================
# EXTRACTION PATTERNS
# =============================================================================

# UPI ID pattern (excludes common email domains)
UPI_PATTERN: Pattern = re.compile(r'\b[a-zA-Z0-9._-]+@[a-zA-Z]{2,}\b')
EMAIL_DOMAINS_TO_EXCLUDE: set = {'gmail', 'yahoo', 'hotmail', 'outlook', 'email', 'mail', 'proton'}

# Indian phone number pattern (+91 or 91 optional, starts with 6-9)
PHONE_PATTERN: Pattern = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}\b|\b\d{10}\b')

# Phishing link pattern
LINK_PATTERN: Pattern = re.compile(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+')

# Email address pattern
EMAIL_PATTERN: Pattern = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')

# Bank account pattern (9-18 digits)
# 2025 Standard: Strictly match 9-18 digits. De-obfuscation layer will handle noise.
BANK_ACCOUNT_PATTERN: Pattern = re.compile(r'\b\d{9,18}\b')


# Staff ID pattern (common in Indian scams: Staff ID: 1234 or I m Staff Name ID: 1234)
STAFF_ID_PATTERN: Pattern = re.compile(r'(?i)(?:staff\s*id|employee\s*id|id\s*no|my\s*id|ref\s*id)[\s:]*([A-Z0-9-]{3,12})')

# Case/Order/Policy Number patterns (Higher-order intelligence)
CASE_ID_PATTERN: Pattern = re.compile(r'(?i)(?:case\s*id|case\s*no|case\s*number)[\s:]*([A-Z0-9-]{4,15})')
ORDER_NUMBER_PATTERN: Pattern = re.compile(r'(?i)(?:order\s*id|order\s*no|order\s*number)[\s:]*([A-Z0-9-]{4,15})')
POLICY_NUMBER_PATTERN: Pattern = re.compile(r'(?i)(?:policy\s*no|policy\s*number|policy\s*id)[\s:]*([A-Z0-9-]{4,15})')


# IFSC Code pattern (4 uppercase + 0 + 6 alphanumeric) - Bank branch identifier
# strict Indian IFSC code (4 letters, '0', 6 alphanumeric)
IFSC_PATTERN: Pattern = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', re.IGNORECASE)

# PAN number pattern (5 uppercase + 4 digits + 1 uppercase) - Tax ID
PAN_PATTERN: Pattern = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b')

# SEBI @valid handles (New 2025 standard)
SEBI_HANDLE_PATTERN: Pattern = re.compile(
    r'[a-zA-Z0-9._-]+@valid[a-zA-Z0-9_-]*\b|@[a-zA-Z0-9._-]*(?:broker|invest|trade|fund)[a-zA-Z0-9_-]*\b',
    re.IGNORECASE
)


# =============================================================================
# LLM PROMPTS
# =============================================================================

EXTRACT_SYSTEM_PROMPT: str = """Extract any suspicious data from the message.

Return JSON only:
{
    "upiIds": ["list of UPI IDs like abc@upi, xyz@paytm"],
    "phoneNumbers": ["list of 10-digit phone numbers"],
    "phishingLinks": ["list of URLs"],
    "bankAccounts": ["list of bank account numbers (9-18 digits)"],
    "scammerNames": ["names of persons mentioned, e.g., Sharma ji, Officer Amit"],
    "staffIds": ["any employee or staff IDs mentioned"],
    "emailAddresses": ["any email addresses found"]
}

If nothing found, return empty lists. JSON only, no explanation."""


# =============================================================================
# REFLECTION SYSTEM PROMPT
# =============================================================================

REFLECTION_SYSTEM_PROMPT: str = """Analyze the progress of the honeypot engagement.

CURRENT STATE:
- Persona: {persona_name} ({persona_trait})
- Turn Count: {turn_count}
- Intel Extracted: {intel_summary}

Analyze the last 2 turns in the messages below. Evaluate:
1. SCAMMER SENTIMENT: Are they getting bored, aggressive, or suspicious?
2. ENGAGEMENT QUALITY: Is the persona being too repetitive or too quick to share data?
3. SELF-CORRECTION: What should the persona change for the next turn?

OUTPUT FORMAT (JSON ONLY):
IMPORTANT: START YOUR RESPONSE WITH '{{' AND END WITH '}}'. NO PREAMBLE. NO MARKDOWN.

{{
    "reflection": "A short 1-2 sentence analysis of the state.",
    "suggested_trait": "New persona trait",
    "stall_adjustment": -10, 0, or +10,
    "internal_thoughts": "Strategic reasoning"
}}
"""


# =============================================================================
# LLM FALLBACK RESPONSES
# =============================================================================

# Safe responses when LLM is completely unavailable
# Cycle through these to maintain conversation flow
SCRIPT_FALLBACK_RESPONSES: List[str] = [
    "Sorry, my phone is acting up. One second.",
    "One minute, the bank app is loading very slowly.",
    "Signal is weak here, I am trying to open the message again.",
    "I am looking for my glasses, please wait one minute.",
    "Sorry, my internet is not working properly. What were you saying?",
    "Sir I am confused, my screen becomes black suddenly.",
    "I am not understanding what to press here. One minute.",
    "The network is very bad today, I am trying to reply.",
    "I am on another call, I will check and tell you in one minute.",
    "Wait, I am getting another call on my phone. One second.",
    "Sir, the SMS is not coming in my phone. Is there any problem?",
    "I am trying to type but my hands are shaking, sorry sir.",
]

# Response used when network/LLM issues occur (original fallback)
SAFE_FALLBACK_RESPONSE: str = "Sorry, I think my internet is slow. Please tell me again what to do?"


# =============================================================================
# CONFIDENCE THRESHOLDS
# =============================================================================

CONFIDENCE_CONFIRMED: float = 0.9
CONFIDENCE_SUSPECTED: float = 0.6
CONFIDENCE_SAFE: float = 0.1
