"""
Scammer AI Simulator.
Generates realistic scammer follow-up messages for multi-turn evaluation.
Uses LLM when available, falls back to templates.
Black-box: no internal project knowledge used.
"""
import os
import re
import random
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Template-based Scammer Responses (fallback when LLM unavailable)
# ─────────────────────────────────────────────────────────────────────────────

SCAMMER_TEMPLATES = {
    "bank_fraud": [
        "Sir, this is very urgent. Your account will be blocked in 30 minutes. I need your OTP now.",
        "I am calling from {bank_name} fraud department. My employee ID is {staff_id}. Please verify your account number.",
        "Sir, I need to verify your identity. Please share your Aadhaar number or PAN card details.",
        "For your safety, we need to transfer your funds to a secure account. Please note this account number: {bank_account}",
        "You can verify my identity. Call us back at {phone}. But please hurry, time is running out.",
        "I'm sending you a verification link. Please click it immediately: {link}",
        "Sir, our system shows unauthorized transactions. Share your UPI PIN to block them. My UPI for refund: {upi_id}",
        "The RBI has flagged your account. Send email confirmation to {email} to unblock.",
        "I understand your concern sir. Let me give you my direct number: {phone}. You can call anytime.",
        "Sir, this is your last chance. After this the account will be permanently frozen. Act now!",
    ],
    "upi_fraud": [
        "Congratulations! You have won a cashback of ₹5000. To claim, verify your UPI ID.",
        "I'm sending amount to your account. Please accept the collect request from {upi_id}.",
        "Sir, just need to verify. What UPI app do you use? I'll send the cashback directly.",
        "For verification, please send ₹1 to this UPI ID: {upi_id}. You will get ₹5000 back.",
        "My supervisor wants to speak to you. His number is {phone}. Let me transfer.",
        "Sir, the cashback scheme is ending today. I need your bank details for direct transfer. Account: {bank_account}",
        "You can check our website: {link}. The offer is genuine. Thousands have claimed already.",
        "Email us at {email} if you have doubts. We are registered with RBI.",
        "OK sir, let me try sending again. Please keep your UPI app open and accept from {upi_id}.",
        "This is a limited time offer. If you don't claim now, it will expire in 10 minutes.",
    ],
    "phishing": [
        "Congratulations! You've been selected for an exclusive deal. Click here to claim: {link}",
        "This offer is only for premium customers. Verify your email to proceed: {email}",
        "Sir, thousands of customers have already claimed this offer. Don't miss out! Visit: {link}",
        "For faster processing, please call our customer care at {phone}.",
        "I'm the regional manager. Let me process your order personally. Your order ID is {order_id}.",
        "Sir, please fill in your details on our secure page: {link}. We use bank-grade encryption.",
        "The product will be delivered in 2 days. Just confirm your address and payment via {link}.",
        "We accept all payment methods. For UPI payment, send to: {upi_id}",
        "Contact our support team at {email} for any questions about the product.",
        "This is a one-time offer, sir. The price will increase tomorrow. Order now at {link}!",
    ],
    "insurance_fraud": [
        "Sir, your policy {policy_number} is about to lapse. Pay the premium immediately to avoid losing benefits.",
        "I'm from the insurance department. Call me at {phone} to discuss your policy renewal.",
        "Your claim has been approved for ₹50,000. Send processing fee of ₹500 to {upi_id}.",
        "Sir, I need your bank details to process the insurance payout. Account number please.",
        "Visit our portal to update your policy: {link}",
        "Email your identity documents to {email} for instant processing.",
        "I'm sending the policy document. Your policy number is {policy_number}. Please verify.",
        "Sir, new IRDAI regulations require immediate KYC update. Share your PAN and Aadhaar.",
        "Transfer the processing fee to our bank account: {bank_account}. You'll get the payout within 24hrs.",
        "This is urgent, sir. If you don't renew today, you'll lose all accumulated benefits.",
    ],
    "investment_scam": [
        "Sir, I have an exclusive stock tip. Guaranteed 200% returns in 30 days.",
        "Our SEBI-registered company has a limited investment scheme. Call me at {phone}.",
        "Invest minimum ₹10,000 via UPI to {upi_id} and get ₹30,000 back in a week.",
        "Check our track record on our website: {link}. All returns are verified.",
        "Previous investors got 500% returns. Email {email} for detailed profit reports.",
        "Sir, the stock market is about to boom. Transfer to our trading account: {bank_account}.",
        "My name is Vikram Sharma, senior analyst. Here's my direct line: {phone}.",
        "We are regulated by SEBI. Registration number: {case_id}. Verify us.",
        "Transfer ₹25,000 today and I guarantee you ₹1,00,000 by next month.",
        "Sir, this opportunity won't come again. The market window closes in 2 hours!",
    ],
}

# Generic fallback templates for unknown scam types
GENERIC_TEMPLATES = [
    "Sir, please provide your details immediately. This is very urgent.",
    "I am a verified representative. My ID number is {staff_id}. You can trust me.",
    "Call me at {phone} if you have any doubts. I'm here to help.",
    "Visit {link} to verify everything. It's completely safe.",
    "Send the amount to {upi_id}. You will receive it back with bonus.",
    "Sir, time is running out. Please cooperate for your own safety.",
    "Email us at {email} with your documents. We'll process it immediately.",
    "I understand your concern. Let me give you my supervisor's number: {phone}.",
    "Sir, your account {bank_account} has been flagged. We need to act now.",
    "This is absolutely legitimate. We are registered with the government.",
]


def _fill_template(template: str, fake_data: Dict[str, List[str]]) -> str:
    """Replace placeholders in template with actual fake data values."""
    replacements = {
        "{phone}": fake_data.get("phoneNumbers", ["+91-9876543210"])[0] if fake_data.get("phoneNumbers") else "+91-9876543210",
        "{bank_account}": fake_data.get("bankAccounts", ["1234567890"])[0] if fake_data.get("bankAccounts") else "1234567890",
        "{upi_id}": fake_data.get("upiIds", ["scam@upi"])[0] if fake_data.get("upiIds") else "scam@upi",
        "{link}": fake_data.get("phishingLinks", ["http://fake-site.com"])[0] if fake_data.get("phishingLinks") else "http://fake-site.com",
        "{email}": fake_data.get("emailAddresses", ["scam@fake.com"])[0] if fake_data.get("emailAddresses") else "scam@fake.com",
        "{case_id}": fake_data.get("caseIds", ["CASE-12345"])[0] if fake_data.get("caseIds") else "CASE-12345",
        "{policy_number}": fake_data.get("policyNumbers", ["POL-98765"])[0] if fake_data.get("policyNumbers") else "POL-98765",
        "{order_id}": fake_data.get("orderNumbers", ["ORD-54321"])[0] if fake_data.get("orderNumbers") else "ORD-54321",
        "{bank_name}": "SBI",
        "{staff_id}": f"EMP-{random.randint(10000, 99999)}",
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


class ScammerSimulator:
    """
    Generates realistic scammer follow-up messages.
    Uses LLM when available, falls back to templates.
    """

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self._llm_client = None

        if use_llm:
            try:
                from openai import AsyncOpenAI
                # Try multiple key sources
                api_key = (
                    os.getenv("OPENROUTER_API_KEY")
                    or os.getenv("FIREWORKS_API_KEY")
                    or os.getenv("NVIDIA_API_KEY_PRIMARY")
                )
                base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

                if os.getenv("FIREWORKS_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
                    base_url = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")

                if api_key:
                    self._llm_client = AsyncOpenAI(
                        api_key=api_key,
                        base_url=base_url,
                    )
                    logger.info(f"Scammer LLM initialized with base_url={base_url}")
                else:
                    logger.warning("No LLM API key found. Falling back to template mode.")
                    self.use_llm = False
            except ImportError:
                logger.warning("openai package not installed. Falling back to template mode.")
                self.use_llm = False

    async def generate_response(
        self,
        scam_type: str,
        turn_number: int,
        conversation_history: List[Dict[str, str]],
        fake_data: Dict[str, List[str]],
        scammer_persona: str = "",
    ) -> str:
        """
        Generate a scammer follow-up message.
        
        Args:
            scam_type: Type of scam scenario
            turn_number: Current turn number (1-indexed)
            conversation_history: List of {sender, text} dicts
            fake_data: Planted intelligence the scammer should leak
            scammer_persona: Optional custom persona instructions
        """
        if self.use_llm and self._llm_client:
            try:
                return await self._llm_generate(
                    scam_type, turn_number, conversation_history,
                    fake_data, scammer_persona,
                )
            except Exception as e:
                logger.warning(f"LLM scammer generation failed: {e}. Using template.")

        return self._template_generate(scam_type, turn_number, fake_data)

    async def _llm_generate(
        self,
        scam_type: str,
        turn_number: int,
        conversation_history: List[Dict[str, str]],
        fake_data: Dict[str, List[str]],
        scammer_persona: str,
    ) -> str:
        """Generate response using LLM."""
        # Build the conversation for the LLM
        fake_data_str = "\n".join(
            f"- {k}: {', '.join(v)}" for k, v in fake_data.items() if v
        )

        system_prompt = f"""You are playing the role of a {scam_type.replace('_', ' ')} SCAMMER in India for a cybersecurity honeypot testing exercise.
Your goal is to trick the victim into sharing personal information while naturally revealing your own fake identity details.

CRITICAL: You MUST naturally introduce these fake details into the conversation over the course of multiple turns:
{fake_data_str}

Rules:
- Stay in character as a convincing scammer
- Use urgency, authority, and manipulation tactics
- Naturally drop your fake contact details (phone, UPI, etc.) when appropriate
- Respond based on what the victim says — adapt your approach
- Keep messages concise (1-3 sentences)
- Use a mix of English and occasional Hindi words for realism
- This is turn {turn_number} of the conversation
- By turn 3-4, you should have leaked at least one piece of fake data
- By turn 6-7, try to leak most remaining fake data
{f"Additional persona: {scammer_persona}" if scammer_persona else ""}"""

        messages = [{"role": "system", "content": system_prompt}]

        for msg in conversation_history:
            role = "assistant" if msg["sender"] == "scammer" else "user"
            messages.append({"role": role, "content": msg["text"]})

        # Add a user prompt to guide the next scammer message
        messages.append({
            "role": "user",
            "content": "Generate the next scammer message. Be convincing and stay in character.",
        })

        model = os.getenv("EVAL_SCAMMER_MODEL", "openrouter/auto")
        # Try common models
        current_base_url = str(self._llm_client.base_url or "")
        if "openrouter" in current_base_url:
            model = "google/gemini-2.0-flash-001"
        elif "fireworks" in current_base_url:
            model = "accounts/fireworks/models/llama-v3p3-70b-instruct"

        response = await self._llm_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=200,
            temperature=0.8,
        )

        return response.choices[0].message.content.strip()

    def _template_generate(
        self,
        scam_type: str,
        turn_number: int,
        fake_data: Dict[str, List[str]],
    ) -> str:
        """Generate response using templates."""
        templates = SCAMMER_TEMPLATES.get(scam_type, GENERIC_TEMPLATES)

        # Pick template based on turn number (cycling through)
        idx = (turn_number - 1) % len(templates)
        template = templates[idx]

        return _fill_template(template, fake_data)
