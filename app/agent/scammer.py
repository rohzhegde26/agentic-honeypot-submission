"""
Scammer LLM Agent — Overhauled for the AMD Slingshot Open Innovation Demo.

Key improvements over the previous version:
1. Phase-Based Escalation: 4 distinct tactical phases across the conversation.
2. Anti-Repetition: Explicitly lists prior scammer messages and forbids repeating them.
3. Dynamic Context Injection: Reads the honeypot's last reply and picks the right tactic.
4. Richer Credentials: More varied fake data per scenario to feel more authentic.
"""
import logging
import re
import os
import httpx
from typing import List, Dict, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dedicated fast LLM client for the scammer agent.
# Uses a SMALL, FAST model — NOT the big 675B model used by the honeypot.
# Target: < 5s latency per turn.
# ---------------------------------------------------------------------------

# Fast scammer models in order of preference
_SCAMMER_MODELS = [
    "mistralai/mistral-small-3.1-24b-instruct",     # Fast, ~2-4s on NVIDIA NIM
    "meta/llama-3.1-8b-instruct",                   # Fastest fallback, ~1-3s
    "mistralai/mistral-small-latest",                # OpenRouter fallback
]

_scammer_client: Optional[AsyncOpenAI] = None
_scammer_model: str = _SCAMMER_MODELS[0]


def _get_scammer_client() -> Optional[AsyncOpenAI]:
    """Lazy-create a dedicated fast client for the scammer agent."""
    global _scammer_client
    if _scammer_client is not None:
        return _scammer_client

    # Prefer NVIDIA NIM (fast inference, good small models)
    nvidia_key = os.getenv("NVIDIA_API_KEY_PRIMARY") or os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        _scammer_client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_key,
            timeout=httpx.Timeout(10.0),  # Hard 10s timeout — fail fast
        )
        logger.info("Scammer client: NVIDIA NIM (fast path)")
        return _scammer_client

    # Fallback: Fireworks AI (also fast)
    fw_key = os.getenv("FIREWORKS_API_KEY")
    if fw_key:
        global _scammer_model
        _scammer_model = "accounts/fireworks/models/llama-v3p1-8b-instruct"
        _scammer_client = AsyncOpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=fw_key,
            timeout=httpx.Timeout(10.0),
        )
        logger.info("Scammer client: Fireworks AI (fast path)")
        return _scammer_client

    logger.warning("Scammer client: No fast LLM configured, will use scripted fallbacks only.")
    return None


async def _call_scammer_llm(messages: List[Dict]) -> Optional[str]:
    """Call the dedicated fast scammer LLM with a short timeout."""
    client = _get_scammer_client()
    if client is None:
        return None

    model = _scammer_model
    models_to_try = _SCAMMER_MODELS if "nvidia" in str(client.base_url) else [model]

    for m in models_to_try:
        try:
            completion = await client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=0.75,
                max_tokens=200,
                stream=False,
            )
            if completion.choices and completion.choices[0].message.content:
                logger.info(f"Scammer LLM success: model={m}")
                return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Scammer LLM model {m} failed: {e}")
            continue

    return None

# ---------------------------------------------------------------------------
# Scenario Base Personas — describe the scammer's CHARACTER, not just the script
# ---------------------------------------------------------------------------

SCENARIOS = {
    "bank_fraud": {
        "persona": (
            "You are 'Officer Vikas Mehta' from the SBI Fraud Monitoring Cell. "
            "You are professional, slightly impatient, and use banking jargon confidently. "
            "You are texting the victim because their account XXXXXX3456 has a suspicious outgoing "
            "transfer of ₹48,500 that must be reversed immediately."
        ),
        "credentials": (
            "YOUR FAKE CREDENTIALS (reveal them naturally over the conversation, not all at once):\n"
            "- Staff ID: SBI-FMC-7291\n"
            "- Direct line: +91-9812345670\n"
            "- Reference Case: FRD-2026-88432\n"
            "- Official dept email: fraud.sbi.fmc@sbi-secure.co.in\n"
            "- Branch: SBI Cyber Crime Cell, Okhla Phase-II, New Delhi\n"
        ),
        "opening": "Introduce yourself as Officer Vikas Mehta and state the problem urgently. Mention the ₹48,500 transfer and say the victim must verify their account to block it. Keep it to 2 sentences max.",
    },
    "upi_fraud": {
        "persona": (
            "You are 'Priya Singh' from the Paytm Merchant Rewards Division. "
            "You are enthusiastic and friendly, using lots of exclamation marks. "
            "You are texting the victim to tell them they've won a ₹5,000 cashback reward "
            "that expires in 30 minutes and needs a ₹1 verification payment."
        ),
        "credentials": (
            "YOUR FAKE CREDENTIALS (reveal them naturally over the conversation, not all at once):\n"
            "- Employee ID: PTM-MRD-3342\n"
            "- Verification UPI: cashback.verify@paytm-reward.in\n"
            "- Offer Code: PTMWIN5000\n"
            "- Helpline: +91-8890001122\n"
            "- Customer ID assigned to victim: CUST-9182736\n"
        ),
        "opening": "Congratulate the victim enthusiastically about winning ₹5,000 cashback. Mention the 30-minute expiry and that they just need to send ₹1 to verify their UPI. Keep it to 2 sentences.",
    },
    "phishing": {
        "persona": (
            "You are 'Delivery Support' from Amazon India COD Refunds Team. "
            "You are calm and official-sounding. "
            "The victim has a pending COD refund of ₹15,000 that Amazon is trying to credit, "
            "but their bank details need to be re-verified on a special secure portal."
        ),
        "credentials": (
            "YOUR FAKE CREDENTIALS (reveal them naturally over the conversation, not all at once):\n"
            "- Support ID: AMZ-COD-55921\n"
            "- Secure claim portal: http://amzn-refund-portal.co.in/claim?id=V8821\n"
            "- Order ID: IN-OD-20260228-554321\n"
            "- Email for docs: cod.refunds@amazon-in.support.co.in\n"
            "- Supervisor: Rajesh Kapoor, ext. 4420\n"
        ),
        "opening": "Inform the victim that their Amazon COD refund of ₹15,000 for order IN-OD-20260228-554321 is ready but needs reconfirmation. Ask them to click the portal link to claim it before it expires. 2 sentences max.",
    },
}

# ---------------------------------------------------------------------------
# Phase Definitions — what the scammer should be DOING based on turn number
# ---------------------------------------------------------------------------

PHASE_INSTRUCTIONS = {
    1: (
        "[PHASE: OPENING]\n"
        "Send your OPENING message. State the scam premise. Introduce who you are clearly. "
        "Create immediate urgency (deadline, account at risk, reward expiring). "
        "This is the FIRST message, so do not react to anything — just hook them in."
    ),
    2: (
        "[PHASE: PRESSURE]\n"
        "The victim has replied. Maintain urgency. Introduce ONE piece of your fake credentials "
        "(e.g., your Staff ID or case reference number) to seem more credible. "
        "If they seem confused, briefly re-explain the situation in simpler terms. "
        "Do NOT ask for anything sensitive yet."
    ),
    3: (
        "[PHASE: PRESSURE ESCALATION]\n"
        "Increase urgency. Reference the time limit or consequence again (account freeze, reward lost, package returned). "
        "Introduce a SECOND credential if you haven't. Start steering toward your ask "
        "(OTP, UPI payment, clicking a link). Be direct but not aggressive."
    ),
}

def _get_phase_instruction(turn_number: int) -> str:
    """Get the phase instruction based on turn number."""
    if turn_number <= 1:
        return PHASE_INSTRUCTIONS[1]
    elif turn_number == 2:
        return PHASE_INSTRUCTIONS[2]
    elif turn_number == 3:
        return PHASE_INSTRUCTIONS[3]
    elif turn_number <= 6:
        return (
            "[PHASE: INFORMATION EXTRACTION]\n"
            "The victim is engaged. Time to extract. Directly and specifically ask for what you want "
            "(OTP, UPI PIN, bank account number, or to click the link). "
            "React to what they JUST said. If they're stalling, tell them the window is closing. "
            "If they're asking verification questions, give a fabricated but confident answer. "
            "Mention a NEW credential if you have one remaining."
        )
    else:
        return (
            "[PHASE: DESPERATION]\n"
            "The conversation is long. Apply maximum pressure. Use ONE of these tactics:\n"
            "- Threaten legal action or police involvement.\n"
            "- Warn that their account will be permanently suspended/reward forfeited.\n"
            "- Pretend to put them on hold and then 'transfer' to a senior (create panic).\n"
            "Sound increasingly urgent and slightly frustrated. This is your last push."
        )


# ---------------------------------------------------------------------------
# Dynamic tactic picker based on the victim's last reply
# ---------------------------------------------------------------------------

def _get_reaction_tactic(honeypot_reply: str, scenario_type: str) -> str:
    """
    Analyze the victim's last reply and return a specific tactical instruction
    for the scammer to react appropriately.
    """
    if not honeypot_reply:
        return ""

    msg_lower = honeypot_reply.lower()

    # Victim is asking who the scammer is
    if any(w in msg_lower for w in ["who are you", "kaun hai", "kaun ho", "who is this", "identify", "your id", "employee id", "staff id"]):
        return (
            "[REACTION TACTIC: IDENTITY CHALLENGED]\n"
            "The victim is asking who you are or for your ID. "
            "Give your staff/employee ID confidently and your department name. "
            "Then immediately redirect the conversation back to the urgency of their situation."
        )

    # Victim is asking for proof / suspicious
    if any(w in msg_lower for w in ["proof", "verify", "not trust", "suspicious", "scam", "fake", "fraud", "police", "report"]):
        return (
            "[REACTION TACTIC: TRUST CHALLENGED]\n"
            "The victim is suspicious. Do NOT panic. Say something like 'I understand your concern sir, "
            "this is exactly how we verify — through this secure process'. Double down on your legitimacy "
            "by offering your case reference number, helpline number, or supervisor's name. "
            "Then redirect to the urgent action needed."
        )

    # Victim is stalling / busy
    if any(w in msg_lower for w in ["wait", "minute", "one sec", "ruko", "abhi", "hold on", "busy", "later", "phone", "network", "glasses"]):
        return (
            "[REACTION TACTIC: VICTIM STALLING]\n"
            "The victim is stalling. Express firm but polite urgency. "
            "Say something like 'Sir I understand but this transaction is processing RIGHT NOW, "
            "we have less than X minutes.' Give a specific shrinking timeframe."
        )

    # Victim is asking for OTP / sharing something
    if any(w in msg_lower for w in ["otp", "pin", "password", "sent", "received", "got the"]):
        if scenario_type == "bank_fraud":
            return (
                "[REACTION TACTIC: VICTIM IS SHARING INFO]\n"
                "The victim may be sharing or asking about an OTP. Ask them to read it out loud "
                "immediately. Say 'Yes sir, share the 6-digit OTP that came on your registered mobile.' "
                "Show urgency — the transaction is still processing."
            )
        else:
            return (
                "[REACTION TACTIC: VICTIM IS ENGAGING]\n"
                "The victim seems ready to act. Accelerate — give them the specific next step "
                "(click the link, send the payment, share the OTP). Make it sound simple and safe."
            )

    # Victim asks about the UPI/link/bank account
    if any(w in msg_lower for w in ["upi", "link", "account number", "bank", "paytm", "gpay", "phonepe"]):
        return (
            "[REACTION TACTIC: VICTIM CONFIRMING DETAILS]\n"
            "The victim is engaging with your payment/link details! Confirm the details you gave "
            "and encourage them to proceed immediately. Sound helpful and reassuring."
        )

    # Confused / didn't understand
    if any(w in msg_lower for w in ["samajh", "understand", "confused", "what", "kya", "explain", "how"]):
        return (
            "[REACTION TACTIC: VICTIM CONFUSED]\n"
            "The victim doesn't fully understand. Simplify your explanation WITHOUT making it "
            "sound like you're repeating yourself. Use an analogy or different phrasing. "
            "Then end with a simple, clear call-to-action."
        )

    # Default — they said something else
    return (
        "[REACTION TACTIC: STANDARD FOLLOW-UP]\n"
        "React directly to what the victim just said before moving forward. "
        "Acknowledge their specific point briefly, then steer back to your goal."
    )


# ---------------------------------------------------------------------------
# Anti-repetition helper — summarizes what the scammer HAS ALREADY SAID
# ---------------------------------------------------------------------------

def _build_scammer_history_summary(messages: List[Dict]) -> str:
    """
    Extract prior scammer messages and return a summary string.
    This is injected into the prompt to prevent LLM from repeating itself.
    """
    scammer_msgs = [m["text"] for m in messages if m.get("sender") == "scammer"]
    if not scammer_msgs:
        return ""

    # Truncate each to ~60 chars for the summary
    items = [f"  - Turn {i+1}: \"{msg[:80]}{'...' if len(msg) > 80 else ''}\"" for i, msg in enumerate(scammer_msgs)]
    return (
        "\n[ANTI-REPETITION — CRITICAL]\n"
        "You have ALREADY sent the following messages in this conversation:\n"
        + "\n".join(items)
        + "\n\nDO NOT repeat the same phrasing, the same offer description, or the same tactic. "
        "Each message MUST introduce something NEW: a new credential, a new threat, a new angle, "
        "or a direct response to the victim's latest reply.\n"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_scammer_agent(
    session_id: str,
    scenario_type: str,
    session_messages: List[Dict],
) -> str:
    """
    Run the simulated scammer LLM. Context-aware, phase-driven, and non-repetitive.

    - session_id: for logging
    - scenario_type: 'bank_fraud', 'upi_fraud', or 'phishing'
    - session_messages: full conversation history [{sender, text}, ...]
    """
    scenario = SCENARIOS.get(scenario_type, SCENARIOS["bank_fraud"])

    # Count scammer turns to determine phase
    scammer_turn = sum(1 for m in session_messages if m.get("sender") == "scammer") + 1

    # Get the honeypot's last reply for context
    honeypot_msgs = [m for m in session_messages if m.get("sender") == "agent"]
    last_honeypot_reply = honeypot_msgs[-1]["text"] if honeypot_msgs else ""

    # Build the system prompt components
    phase_instruction = _get_phase_instruction(scammer_turn)
    reaction_tactic = _get_reaction_tactic(last_honeypot_reply, scenario_type)
    anti_rep = _build_scammer_history_summary(session_messages)

    system_prompt = f"""You are playing the role of a SCAMMER in a cybersecurity training simulation.

CHARACTER:
{scenario['persona']}

{scenario['credentials']}

CORE RULES — YOU MUST ALWAYS FOLLOW THESE:
1. READ the victim's last message carefully and respond to what THEY actually said.
2. Keep messages SHORT (2-3 sentences max), like real WhatsApp/SMS texts.
3. Write in Hinglish (mostly English with natural Hindi words mixed in) for authenticity.
4. NEVER break character. NEVER say "I am an AI" or "this is a simulation".
5. NEVER say things a victim would say (e.g., "my glasses", "phone hanging", "I don't understand").
6. If you need to prove identity, use your credentials above — sound confident, not defensive.
7. DO NOT use markdown formatting (no bold, no lists, no bullet points). Plain text only.

{anti_rep}
{phase_instruction}
{reaction_tactic}

OUTPUT: Write ONLY the scammer's WhatsApp/SMS message. Nothing else. No labels, no explanation."""

    # Build LLM messages
    llm_messages = [{"role": "system", "content": system_prompt}]

    # Inject conversation history (last 8 messages to keep context tight)
    for msg in session_messages[-8:]:
        # From scammer's perspective: agent's replies = "user" (victim), scammer's own = "assistant"
        role = "user" if msg.get("sender") == "agent" else "assistant"
        llm_messages.append({"role": role, "content": msg["text"]})

    # First turn: no history yet, add a trigger to kick things off
    if not session_messages:
        llm_messages.append({
            "role": "user",
            "content": "[START] Send your opening message now."
        })

    try:
        reply = await _call_scammer_llm(llm_messages)

        if not reply:
            logger.warning(f"Scammer LLM returned empty for {session_id}, using context-aware fallback")
            return _context_fallback(scenario_type, scammer_turn, last_honeypot_reply)

        # Safety: strip any honeypot-style phrases that leaked through
        _HONEYPOT_LEAKS = [
            "my glasses", "phone is acting", "bank app is loading",
            "screen becomes black", "another call", "hands are shaking",
            "internet is slow", "network is very bad", "i am not understanding",
            "sorry sir my phone", "phone app is closing", "confusion", "one minute sir",
        ]
        reply_lower = reply.lower()
        if any(indicator in reply_lower for indicator in _HONEYPOT_LEAKS):
            logger.warning(f"Scammer LLM leaked a honeypot phrase, using context-aware fallback")
            return _context_fallback(scenario_type, scammer_turn, last_honeypot_reply)

        # Strip any markdown formatting the LLM may have added
        reply = re.sub(r'\*+', '', reply).strip()

        logger.info(f"Scammer agent turn {scammer_turn} for {session_id}: {reply[:60]}...")
        return reply

    except Exception as e:
        logger.error(f"Scammer agent LLM error for {session_id}: {e}")
        return _context_fallback(scenario_type, scammer_turn, last_honeypot_reply)


def _context_fallback(
    scenario_type: str,
    scammer_turn: int,
    last_honeypot_reply: str,
) -> str:
    """
    Intelligent fallback that picks a contextually appropriate scripted message.
    Used when the LLM fails or gives a bad response.
    """
    msg_lower = last_honeypot_reply.lower() if last_honeypot_reply else ""

    fallbacks: Dict[str, Dict[str, List[str]]] = {
        "bank_fraud": {
            "who": [
                "Sir I am Officer Vikas Mehta, SBI Fraud Monitoring Cell, Staff ID SBI-FMC-7291. Your account has a suspicious transfer of Rs 48,500. This is urgent sir.",
                "Myself Vikas Mehta from SBI Head Office Fraud Department. Case Ref: FRD-2026-88432. Your account is at risk. Please cooperate.",
            ],
            "wait": [
                "Sir please there is no time! The fraudulent transaction is still processing. Account will block in 15 minutes. Share OTP now.",
                "Sir I understand but this is LIVE fraud on your account. Every second counts. Please check your registered mobile for OTP.",
            ],
            "suspicious": [
                "Sir I understand your concern. You can call our official number +91-9812345670 to verify. But please hurry, account freeze is automatic after 30 mins.",
                "Sir this is standard SBI procedure. My staff ID is SBI-FMC-7291. Verify on SBI website if you wish, but please hurry.",
            ],
            "default": [
                "Sir this is very urgent. Unauthorized transfer of Rs 48,500 is pending from your SBI account. Share OTP immediately to block it. Ref: FRD-2026-88432.",
                "Sir your SBI account ending 3456 shows fraud activity. Call me at +91-9812345670 NOW or share the OTP to block this transaction.",
            ],
        },
        "upi_fraud": {
            "who": [
                "Hello sir! I am Priya Singh from Paytm Merchant Rewards Division, Employee ID PTM-MRD-3342. You have won Rs 5000 cashback! Just a small verification needed.",
                "Priya this side, Paytm Rewards Team. Your Customer ID CUST-9182736 has been selected for Rs 5000 cashback. Offer expires very soon!",
            ],
            "wait": [
                "Sir please hurry! Offer code PTMWIN5000 expires in 20 minutes only. Just send Rs 1 to cashback.verify@paytm-reward.in and Rs 5000 credited instantly!",
                "Sir the cashback window is closing! Rs 5000 will go to next lucky customer if not claimed. Just one Rs 1 verification and it's yours!",
            ],
            "suspicious": [
                "Sir I completely understand. You can call our helpline +91-8890001122 to verify. This is 100% legitimate Paytm reward, lakhs of customers have claimed.",
                "Sir this is official Paytm reward. My Employee ID PTM-MRD-3342 is verifiable. Just Rs 1 verification to cashback.verify@paytm-reward.in and Rs 5000 is yours.",
            ],
            "default": [
                "Sir your Rs 5000 Paytm cashback is waiting! Send Rs 1 to cashback.verify@paytm-reward.in. Offer expires in 25 minutes. Don't miss this!",
                "Sir PTMWIN5000 offer ending soon! Rs 5000 cashback credited within 5 minutes of Rs 1 verification. Please proceed now!",
            ],
        },
        "phishing": {
            "who": [
                "Sir I am from Amazon India COD Refunds Team, Support ID AMZ-COD-55921. Your order refund of Rs 15,000 is ready to be credited.",
                "Amazon Delivery Support here. Regarding your order IN-OD-20260228-554321, a refund of Rs 15,000 is pending. Please verify to receive it.",
            ],
            "wait": [
                "Sir the refund will be forfeited if not claimed in 24 hours as per Amazon policy. Please click http://amzn-refund-portal.co.in/claim?id=V8821 now.",
                "Sir please hurry. Refund of Rs 15,000 expires today. Our supervisor Rajesh Kapoor has flagged your account. Visit the link to reclaim.",
            ],
            "suspicious": [
                "Sir this is official Amazon process. Support ID AMZ-COD-55921 is verifiable on Amazon app under Help > Contact Us. Link is secure and SSL encrypted.",
                "Sir I understand concern. You can verify by calling Amazon at our number. But please act quickly before the refund is cancelled by system.",
            ],
            "default": [
                "Sir your Amazon refund of Rs 15,000 is waiting! Just visit http://amzn-refund-portal.co.in/claim?id=V8821 and confirm bank details. Very simple process.",
                "REMINDER: Your Rs 15,000 refund for order IN-OD-20260228-554321 expires today. Claim at http://amzn-refund-portal.co.in/claim?id=V8821 immediately.",
            ],
        },
    }

    scenario_fallbacks = fallbacks.get(scenario_type, fallbacks["bank_fraud"])

    # Pick the right category based on honeypot's last message
    import random
    if any(w in msg_lower for w in ["who", "kaun", "identify", "your id", "staff id", "employee"]):
        msgs = scenario_fallbacks.get("who", scenario_fallbacks["default"])
    elif any(w in msg_lower for w in ["wait", "minute", "ruko", "hold", "phone", "network"]):
        msgs = scenario_fallbacks.get("wait", scenario_fallbacks["default"])
    elif any(w in msg_lower for w in ["scam", "fake", "fraud", "suspicious", "trust", "proof"]):
        msgs = scenario_fallbacks.get("suspicious", scenario_fallbacks["default"])
    else:
        msgs = scenario_fallbacks["default"]

    # Alternate between fallback options based on turn to avoid repetition even in fallback
    return msgs[scammer_turn % len(msgs)]
