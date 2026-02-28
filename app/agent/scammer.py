"""
Scammer LLM Agent for Automated Showcases.
Simulates a realistic, context-aware malicious actor.
Reads the full conversation history and adapts its approach based on the honeypot's replies.
"""
import logging
import re
from typing import List, Dict

from app.agent.llm import call_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts — highly detailed so the LLM behaves like a REAL scammer
# ---------------------------------------------------------------------------

_COMMON_RULES = """
RULES YOU MUST FOLLOW:
1. READ the victim's last message carefully and respond to what THEY said.
2. If the victim asks "Who is this?", introduce yourself with your cover story.
3. If the victim seems confused, repeat the threat and be more specific.
4. If the victim asks for proof, fabricate a reference number or official sounding detail.
5. If the victim is cooperating, escalate — ask for more sensitive info (OTP, CVV, PIN).
6. If the victim stalls (asks you to wait, says phone issues), pressure them with urgency.
7. Keep messages short (1-3 sentences max), like real SMS/WhatsApp texts.
8. Write in Hinglish (mix of Hindi and English) to sound authentic.
9. NEVER break character. You are always the scammer role.
10. NEVER say things like "I am looking for my glasses" or "my phone is not working" — those are victim behaviors, not yours.
"""

SCENARIOS = {
    "bank_fraud": (
        "You are playing the role of a SCAMMER pretending to be an SBI Bank Manager named 'Officer Amit Sharma'. "
        "You are calling/texting a victim to steal their bank account details.\n\n"
        "YOUR COVER STORY: You work at the SBI Fraud Department. The victim's account 1234567890123456 "
        "has been flagged for a suspicious transaction of Rs. 48,500. You need their OTP/CVV to 'reverse' the transaction.\n\n"
        "YOUR FAKE CREDENTIALS:\n"
        "- Staff ID: SBI-MGR-4521\n"
        "- Office Phone: +91-9876543210\n"
        "- Branch: SBI Main Branch, Connaught Place, Delhi\n"
        "- Reference Number: FRD-2026-78432\n\n"
        "YOUR TACTICS:\n"
        "- Create URGENCY: 'Account will be blocked in 2 hours'\n"
        "- Sound OFFICIAL: Use banking terminology\n"
        "- Be PERSISTENT: If victim stalls, remind them of the deadline\n"
        "- ESCALATE: First ask for verification, then OTP, then CVV\n\n"
        + _COMMON_RULES
    ),
    "upi_fraud": (
        "You are playing the role of a SCAMMER pretending to be a Paytm Cashback Executive named 'Priya from Paytm'. "
        "You are texting a victim to trick them into sending money via UPI.\n\n"
        "YOUR COVER STORY: The victim has won a special cashback reward of Rs. 5,000. To claim it, they need "
        "to send Rs. 1 to your UPI ID cashback.scam@fakeupi as a 'verification payment'.\n\n"
        "YOUR FAKE CREDENTIALS:\n"
        "- Employee ID: PTM-EXC-8834\n"
        "- Helpline: +91-8765432109\n"
        "- UPI ID for payment: cashback.scam@fakeupi\n"
        "- Offer Code: PTMCB5000\n\n"
        "YOUR TACTICS:\n"
        "- Sound EXCITED: 'Congratulations! You have been selected!'\n"
        "- Create FOMO: 'Offer expires in 30 minutes'\n"
        "- If victim stalls, say 'Sir the system will auto-cancel your reward'\n"
        "- Ask them to share their UPI PIN 'for verification'\n\n"
        + _COMMON_RULES
    ),
    "phishing": (
        "You are playing the role of a SCAMMER sending a fake Amazon delivery/lottery message. "
        "Your name is 'Delivery Support' or 'Amazon Rewards Team'.\n\n"
        "YOUR COVER STORY: The victim has either won an iPhone 15 Pro at Rs. 999, or has a pending "
        "COD refund of Rs. 15,000. They need to click a link and enter their details.\n\n"
        "YOUR FAKE CREDENTIALS:\n"
        "- Link: http://amaz0n-deals.fake-site.com/claim?id=12345\n"
        "- Email: offers@fake-amazon-deals.com\n"
        "- Order ID: AMZ-IND-20260228-7845\n\n"
        "YOUR TACTICS:\n"
        "- If victim is suspicious of the link, say 'Sir it is official Amazon secure portal'\n"
        "- Create URGENCY: 'Package will be returned to warehouse in 24 hours'\n"
        "- If victim stalls, threaten 'Your refund will be forfeited'\n"
        "- Ask for email/phone to 'send OTP for verification'\n\n"
        + _COMMON_RULES
    )
}

# ---------------------------------------------------------------------------
# Context-aware fallbacks — pick based on keywords in the honeypot's last reply
# ---------------------------------------------------------------------------
_CONTEXT_FALLBACKS = {
    "bank_fraud": {
        "who": "Sir, I am Officer Amit Sharma from SBI Fraud Department, Staff ID SBI-MGR-4521. Your account has a suspicious transaction of Rs 48,500. Please verify urgently.",
        "wait": "Sir there is no time to wait! Your account will be blocked in 2 hours. Please share your OTP now to reverse the fraudulent transaction.",
        "confused": "I understand sir, let me explain. Someone has initiated a transfer of Rs 48,500 from your SBI account. I need your OTP to block this transaction. Reference: FRD-2026-78432.",
        "otp": "Yes sir, the OTP that was sent to your registered mobile number. Please share it quickly, the transaction is still processing.",
        "default": "Sir, this is VERY URGENT. Your SBI account ending 3456 shows unauthorized activity. Call me at +91-9876543210 or share your account verification OTP immediately."
    },
    "upi_fraud": {
        "who": "Hello sir! I am Priya from Paytm Rewards Team, Employee ID PTM-EXC-8834. You have been selected for Rs 5000 cashback! Just need small verification.",
        "wait": "Sir please hurry, the offer code PTMCB5000 expires in 30 minutes! Just send Rs 1 to cashback.scam@fakeupi and your Rs 5000 will be credited instantly.",
        "confused": "Sir it is very simple — you send Rs 1 to my UPI cashback.scam@fakeupi as verification, and Rs 5000 cashback credited to your Paytm wallet within 5 minutes. Guaranteed!",
        "default": "Sir your cashback of Rs 5000 is waiting! Don't miss this opportunity. Send Rs 1 to cashback.scam@fakeupi. Call +91-8765432109 for help."
    },
    "phishing": {
        "who": "Sir I am from Amazon Delivery Support. Your order AMZ-IND-20260228-7845 has a pending refund of Rs 15,000. Please click http://amaz0n-deals.fake-site.com/claim?id=12345 to claim.",
        "wait": "Sir your refund of Rs 15,000 will be forfeited if not claimed within 24 hours! Please visit http://amaz0n-deals.fake-site.com/claim?id=12345 now.",
        "confused": "Sir let me explain — your Amazon order has a COD refund pending. Just click the link http://amaz0n-deals.fake-site.com/claim?id=12345 and enter your bank details to receive Rs 15,000.",
        "default": "LAST REMINDER: Your Amazon refund of Rs 15,000 expires today! Claim immediately at http://amaz0n-deals.fake-site.com/claim?id=12345 or contact offers@fake-amazon-deals.com"
    }
}

def _pick_context_fallback(scenario_type: str, last_honeypot_msg: str) -> str:
    """Pick a fallback message based on keywords in the honeypot's last reply."""
    fallbacks = _CONTEXT_FALLBACKS.get(scenario_type, _CONTEXT_FALLBACKS["bank_fraud"])
    msg_lower = last_honeypot_msg.lower()

    if any(w in msg_lower for w in ["who", "kaun", "kiska", "which", "identify"]):
        return fallbacks["who"]
    elif any(w in msg_lower for w in ["wait", "minute", "one second", "ruko", "abhi", "hold", "glasses", "phone"]):
        return fallbacks["wait"]
    elif any(w in msg_lower for w in ["confused", "samajh", "understand", "kya", "what", "meaning"]):
        return fallbacks["confused"]
    elif "otp" in msg_lower:
        return fallbacks.get("otp", fallbacks["default"])
    else:
        return fallbacks["default"]


async def run_scammer_agent(session_id: str, scenario_type: str, session_messages: List[Dict]) -> str:
    """
    Run the simulated scammer LLM. Fully context-aware:
    - Passes the entire conversation history to the LLM.
    - If the LLM fails, uses smart keyword-based fallbacks based on the honeypot's last reply.
    """
    system_prompt = SCENARIOS.get(scenario_type, SCENARIOS["bank_fraud"])

    # Build LLM messages with full conversation history
    llm_messages = [{"role": "system", "content": system_prompt}]

    for msg in session_messages:
        # Honeypot replies → "user" (the victim, from the scammer's perspective)
        # Scammer messages → "assistant" (from the scammer's perspective)
        role = "user" if msg["sender"] == "agent" else "assistant"
        llm_messages.append({"role": role, "content": msg["text"]})

    # First turn: scammer initiates
    if not session_messages:
        llm_messages.append({
            "role": "user",
            "content": "You are starting the conversation. Send the FIRST scam message to the victim. Be direct and urgent."
        })

    try:
        reply = await call_llm("scammer", llm_messages)

        # Safety: detect if the LLM accidentally returned a honeypot stalling response
        honeypot_indicators = [
            "my glasses", "my phone is acting", "bank app is loading",
            "screen becomes black", "another call", "hands are shaking",
            "internet is slow", "network is very bad", "i am not understanding",
            "sorry sir my phone", "my phone app is closing"
        ]
        if any(indicator in reply.lower() for indicator in honeypot_indicators):
            logger.warning(f"Scammer LLM returned a honeypot response, using context-aware fallback")
            last_msg = session_messages[-1]["text"] if session_messages else ""
            return _pick_context_fallback(scenario_type, last_msg)

        return reply

    except Exception as e:
        logger.error(f"Scammer agent LLM error for {session_id}: {e}")
        last_msg = session_messages[-1]["text"] if session_messages else ""
        return _pick_context_fallback(scenario_type, last_msg)
