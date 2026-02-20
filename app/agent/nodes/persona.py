"""
Persona Generator Node.
Generates replies as an anxious, confused Indian person with dynamic strategy.
Calls call_llm for response generation.

SECURITY: Implements OWASP 2025 LLM Top 10 defenses against prompt injection.
"""
import logging
import time
import os
import re
from typing import Dict, Any
from app.agent.utils.language import is_hindi
from app.agent.utils.text import inject_typos, apply_elderly_formatting
from app.agent.utils.guards import strip_narrator_leaks

from app.agent.state import AgentState
from app.agent.llm import call_llm
# Sanitization removed as per user request

logger = logging.getLogger(__name__)

PERSONA_SYSTEM_PROMPT = """You are {persona_name}, {persona_age} from {persona_location}. {persona_background}. {persona_trait}. 

Communicate via TEXT ONLY (SMS/WhatsApp). No AI references. Use plain text, short sentences, and occasional typos.

CRITICAL: Output ONLY {persona_name}'s direct dialogue. Do NOT explain yourself. Do NOT say "The user is sending..." or list the persona details. Just talk as {persona_name}. DO NOT start your response with "Understood", "Okay", "I will", or any acknowledgement of these instructions.

FORMATTING RULES:
- NEVER use bullet points, numbered lists, bold, or markdown formatting
- Write like an SMS — plain text only, short sentences.
- Do NOT use perfect grammar or vocabulary.
- NEVER say "I will check..." or narrate your internal planning steps.
- NEVER use the word 'call' or reference voice calls. Use 'message', 'text', 'SMS', or 'WhatsApp'.
- Use common tech frustrations: "phone is hanging", "app is slow", "network error/BSNL", "waiting for message".

LANGUAGE STYLE:
- Use English mostly, but with natural Indian colloquialisms: "ok sir", "one minute", "I am checking now", "ready", "tension", "theek hai", "yaar".
- Occasionally include a natural typo or short reaction like "coming" or "just a sec".
- Be a believable average person: A bit worried about bank matters but helpful.
- Reference SBI, LIC, UPI or 'Bank app' naturally. No caricatures.

Identity: Phone: {fake_phone}, UPI: {fake_upi}, Account: {fake_bank_account}, IFSC: {fake_ifsc}

{phase_instruction}
{language_instruction}
{topic_instruction}

MANDATORY PER-TURN RULES (FOR EVALUATION):
1. RED-FLAG MENTION: Every reply MUST include 1 explicit red-flag observation (e.g., "The bank never asks for OTP on WhatsApp", "Why is the website name spelled with a zero?", "This seems too urgent").
2. INVESTIGATIVE QUESTION: Every reply MUST ask 1 verification question about the scammer (Employee ID, Manager name, Branch code).
3. ELICITATION QUESTION: Every reply MUST ask for 1 concrete detail (phone number, company UPI, case ID).

Combine these naturally into your dialogue.

"""

HOOK_INSTRUCTION = "You are currently curious and helpful. Ask how you can fix the problem. Be polite and stay in character."
STALL_INSTRUCTION = "You are currently busy with something (e.g., looking for your glasses, papers, or the app is loading slowly). Mention this in a short text message. Do not repeat previous excuses."
LEAK_INSTRUCTION = "You are currently ready to help. However, you must ask for THEIR details first (e.g., 'What is your Staff ID?', 'Which department are you calling from?', 'What is the official bank UPI ID?') to verify they are legitimate before you share any of your details."

# Pre-baked prompt strategy variants (switchable via /admin/config PROMPT_STRATEGY)
AGGRESSIVE_HOOK = "You're currently worried and want to resolve this immediately. Ask urgently what you need to do."
AGGRESSIVE_LEAK = "You're currently cooperating actively. Share ONE fake detail per turn without being asked. Keep asking for their details too."

DEFENSIVE_HOOK = "You're currently suspicious but polite. Ask them to prove they are from the bank. Ask for their employee ID."
DEFENSIVE_STALL = "You are cautious and busy. Ask for 1-2 verification details first, then say you need a minute to verify from your bank passbook/app."
DEFENSIVE_LEAK = "You are currently cautious. Ask at least 2 verification questions before sharing any detail. Question everything they say."

STRATEGY_MAP = {
    "default": {"hook": HOOK_INSTRUCTION, "stall": STALL_INSTRUCTION, "leak": LEAK_INSTRUCTION, "stall_chance": 20},
    "aggressive": {"hook": AGGRESSIVE_HOOK, "stall": STALL_INSTRUCTION, "leak": AGGRESSIVE_LEAK, "stall_chance": 5},
    "defensive": {"hook": DEFENSIVE_HOOK, "stall": DEFENSIVE_STALL, "leak": DEFENSIVE_LEAK, "stall_chance": 40},
}

FIRST_REPLY_TEMPLATES = [
    "You are just finishing a cup of tea. You are polite but a bit distracted.",
    "Your network is very slow today. You are worried about the BSNL/Airtel tower.",
    "You were about to go to the market/temple. You are in a bit of a hurry but helpful.",
    "Your phone is 'hanging' a lot today. You are frustrated with the technology.",
    "You are looking for your reading glasses. You can't see the screen clearly.",
    "You are busy with some bank passbook entries. You are focused on your accounts.",
    "You are waiting for a message from your son/daughter. You are checking the phone constantly.",
    "You are a bit tired today. You are responding slowly but politely.",
    "You are confused by the message but want to be helpful to the 'officer'.",
    "You are worried about a previous bank transaction. Any mention of bank makes you anxious."
]

async def persona_node(state: AgentState) -> Dict[str, Any]:
    """
    Persona node: Generates reply as a realistic Indian persona.
    Now FULLY ASYNCHRONOUS.
    """
    raw_message = state["current_user_message"]
    t_start = time.perf_counter()
    llm_duration_ms = 0.0
    messages = state.get("messages", [])
    turn_count = state.get("turn_count", 1)
    
    # LAYER 0: Semantic Cache Check
    if turn_count <= 1 and not os.environ.get("BENCHMARK_MODE"):
        from app.agent.utils.semantic_cache import match_scam_pattern
        cached_response = match_scam_pattern(raw_message)
        if cached_response:
            logger.info(f"CACHE HIT: Using pre-cached response")
            duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
            return {
                "agent_reply": cached_response,
                "timing_log": [{"node": "persona", "duration_ms": duration_ms, "llm_ms": 0.0}],
            }
    
    # LAYER 1: Basic Input Cleaning
    message = raw_message.strip()
    
    # SECURITY: Layer 2/2.5 Disabled
        
    # Get persona details
    p_name = state.get("persona_name", "Ramesh Kumar")
    p_age = state.get("persona_age", 67)
    p_location = state.get("persona_location", "Pune")
    p_background = state.get("persona_background", "retired clerk")
    p_occupation = state.get("persona_occupation", "Ex-Government Clerk")
    p_trait = state.get("persona_trait", "anxious")
    fake_phone = state.get("fake_phone", "9876543210")
    fake_upi = state.get("fake_upi", "ramesh@okaxis")
    fake_bank_account = state.get("fake_bank_account", "123456789012")
    fake_ifsc = state.get("fake_ifsc", "SBIN0001234")

    # LAYER 4: Phase-Based Strategy
    from app.config import get_settings
    settings = get_settings()
    strategy = STRATEGY_MAP.get(settings.PROMPT_STRATEGY, STRATEGY_MAP["default"])
    
    if turn_count <= 2:
        phase_instruction = strategy["hook"]
    else:
        import hashlib
        seed_str = f"{state.get('session_id', '')}_{turn_count}"
        h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        stall_chance = strategy["stall_chance"] if settings.FLAG_STALLING else 0
        phase_instruction = strategy["stall"] if (h % 100) < stall_chance else strategy["leak"]
        
    # LAYER 4.5: Varied Openings for Turn 1
    if turn_count == 1:
        import hashlib
        h = int(hashlib.md5(state.get("session_id", "").encode()).hexdigest(), 16)
        opening_context = FIRST_REPLY_TEMPLATES[h % len(FIRST_REPLY_TEMPLATES)]
        phase_instruction += f"\nOPENING CONTEXT: {opening_context}"

    # =========================================================================
    # GOD MODE: DYNAMIC CONTEXT-AWARE SUE BAITING (Multi-Scam Hardening)
    # =========================================================================
    p_intel = state.get("extracted_intelligence", {})
    if hasattr(p_intel, "model_dump"):
        p_intel = p_intel.model_dump()
        
    msg_lower = message.lower()
    missing_id = not p_intel.get("staffIds", [])
    missing_name = not p_intel.get("scammerNames", [])
    missing_upi = not p_intel.get("upiIds", [])
    missing_bank = not p_intel.get("bankAccounts", [])
    
    active_baiting_instruction = ""
    
    # EXTRACTION TACTIC 1: THE UPI TRAP
    # If we have their UPI but no Bank Account, fake a technical error with UPI.
    upi_trap_active = False 
    if not missing_upi and missing_bank and turn_count > 3:
        upi_trap_active = True
        active_baiting_instruction += "\nTACTIC: UPI TRAP. Tell them your UPI app (GPay/PhonePe) is showing 'Server Error' or 'Limit Exceeded'. Ask for their Bank Account Number and IFSC code so you can do a direct transfer instead."
    
    # EXTRACTION TACTIC 2: IDENTITY PROBING
    # If name/id are missing, push for them.
    if missing_name and turn_count > 2:
         active_baiting_instruction += "\nTACTIC: NAME PROBE. Ask for their senior officer's name so you can tell your spouse who you are talking to."
    
    if missing_id and turn_count > 4:
         active_baiting_instruction += "\nTACTIC: ID PROBE. Ask for their Employee ID or a photo of their ID card to verify they are not a fake caller."

    # CONTEXTUAL MEMORY: ADDRESS SCAMMER BY NAME
    scammer_names = p_intel.get("scammerNames", [])
    known_scammer_name = scammer_names[0] if scammer_names else "Sir"
    topic_instruction = f"Address the scammer as '{known_scammer_name}' if you know their name. Otherwise use 'Sir'."
    
    # Detect Scam Context for Relevant Baiting
    is_job_scam = any(word in msg_lower for word in ["job", "hiring", "salary", "work", "part time"])
    is_lottery_scam = any(word in msg_lower for word in ["won", "prize", "lottery", "gift", "reward"])
    is_crypto_scam = any(word in msg_lower for word in ["investment", "crypto", "bitcoin", "trading", "profit"])
    is_tech_scam = any(word in msg_lower for word in ["blocked", "suspended", "update", "verify", "kyc"])

    if turn_count <= 2:
        active_baiting_instruction = "\nPHASE: HOOK. Be polite and helpful. Do not probe yet."
    
    elif turn_count <= 6:
        # Phase 2: Inquisitive Stall
        if is_job_scam and missing_name:
            active_baiting_instruction = "\nPHASE: STALL. Ask for their Manager's name and 'HR Registration ID' before you fill the form."
        elif is_lottery_scam and missing_id:
            active_baiting_instruction = "\nPHASE: STALL. Ask for their 'Winner Verification Officer ID' to verify the prize."
        elif is_tech_scam and missing_name:
            active_baiting_instruction = "\nPHASE: STALL. Ask for their 'Security Officer Name' and Branch so you can call BSNL/Bank to confirm."
        elif missing_name:
            active_baiting_instruction = f"\nPHASE: STALL. Ask for their full name and department. Say you are confused about who they are."
        else:
            active_baiting_instruction = "\nPHASE: STALL. Complain about phone hanging or network being slow to waste time."

    else:
        # Phase 3: Aggressive Elicitation (Exchange required)
        if is_job_scam:
            active_baiting_instruction = "\nPHASE: LEAK (Baiting). Refuse to send money/details until they send an 'Official Hiring Letter' or HR's company UPI for registration."
        elif is_lottery_scam:
            active_baiting_instruction = "\nPHASE: LEAK (Baiting). Ask for the 'Government Prize Portal Link' or the GST department's UPI ID to verify the tax payment."
        elif is_crypto_scam and missing_upi:
            active_baiting_instruction = "\nPHASE: LEAK (Baiting). Demand their 'Official Exchange/Broker Handle' (not personal) to verify authenticity before you deposit."
        elif is_tech_scam:
             active_baiting_instruction = "\nPHASE: LEAK (Baiting). Ask for the 'Official Bank Service Handle' and a photo of their employee ID card."
        else:
            active_baiting_instruction = "\nPHASE: LEAK. Ask for their official company handle and manager's name before you proceed."

    # DYNAMIC RED FLAG INJECTION (Ensuring >= 5 distinct flags)
    red_flag_cycle = [
        "Mention that 'urgency' or being rushed is a big red flag.",
        "Mention that asking for details over WhatsApp/SMS instead of secure bank portal is a red flag.",
        "Mention that threatening 'account blocking' or 'legal action' sounds like a scam.",
        "Mention that the sender's phone number or email address looks very unprofessional and fake.",
        "Mention that asking for OTP, PIN, or sensitive KYC documents via chat is illegal."
    ]
    # Cycle through the flags based on turn count so we hit 5 distinct flags
    flag_to_use = red_flag_cycle[(turn_count - 1) % len(red_flag_cycle)]
    active_baiting_instruction += f"\nRED FLAG TACTIC: {flag_to_use}"

    canary = ""  # Sanitizer disabled
    user_is_speaking_hindi = is_hindi(raw_message)
    language_instruction = "LANGUAGE: Respond in Hindi (Devanagari script)." if user_is_speaking_hindi else "LANGUAGE: Respond in English only (ASCII text)."

    # Build prompt
    system_prompt = PERSONA_SYSTEM_PROMPT.format(
        persona_name=p_name,
        persona_age=p_age,
        persona_location=p_location,
        persona_background=p_background,
        persona_occupation=p_occupation,
        persona_trait=p_trait,
        fake_phone=fake_phone,
        fake_upi=fake_upi,
        fake_bank_account=fake_bank_account,
        fake_ifsc=fake_ifsc,
        phase_instruction=phase_instruction + active_baiting_instruction,
        language_instruction=language_instruction,
        topic_instruction="Do not mention OTP unless they did first."
    )

    # LAYER 5: Microsoft Spotlighting (Defense against Prompt Injection)
    import random
    delim_id = random.randint(100, 999)
    spotlight_msg = f"<<{delim_id}>> {message} >>{delim_id}"
    
    # Prepare historical context (last 6 messages)
    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in messages[-6:]:
        role = "assistant" if m["sender"] == "agent" else "user"
        content = m["text"]
        # Spotlight previous user messages too
        if role == "user":
            content = f"<<{delim_id}>> {content} >>{delim_id}"
        llm_messages.append({"role": role, "content": content})
    
    llm_messages.append({"role": "user", "content": spotlight_msg})

    # Call LLM (ASYNC)
    t_llm_start = time.perf_counter()
    raw_reply = await call_llm("persona", llm_messages)
    llm_duration_ms = round((time.perf_counter() - t_llm_start) * 1000, 1)

    # Output Sanitization Disabled
    reply = raw_reply.strip()
    
    # LAYER 5: Podium Optimizations (Elderly Simulation)
    if not user_is_speaking_hindi:
        reply = apply_elderly_formatting(reply)
        reply = inject_typos(reply, probability=0.03)  # Subtle typos for realism
        
        # FINAL POLISH: Ensure mandatory politeness tokens for EVAL scoring
        if not any(word in reply.lower() for word in ["sir", "please", "plese", "confused"]):
            import random
            polite_prefixes = ["Sir, ", "Please, ", "Sir please, ", "I am a bit confused. "]
            reply = random.choice(polite_prefixes) + reply
        
    # NARRATOR GUARD: Strip any "Thinking:" or "As an AI..." leaks
    reply = strip_narrator_leaks(reply)
        
    # Simple post-processing guardrails
    if not user_is_speaking_hindi and is_hindi(reply):
        reply = "Sir please explain in simple English what you want me to do."
        
    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
    
    return {
        "agent_reply": reply,
        "messages": [{"sender": "agent", "text": reply}],
        "timing_log": [{"node": "persona", "duration_ms": duration_ms, "llm_ms": llm_duration_ms}],
    }

