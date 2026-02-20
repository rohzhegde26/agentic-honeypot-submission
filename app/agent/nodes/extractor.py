"""
Extractor Node.
Extracts intelligence from scammer messages using regex and optional LLM reinforcement.
Only updates extracted_intelligence, never overwrites existing values.
"""
import re
import json
import logging
import time
from typing import Dict, Any, List

from app.agent.state import AgentState

from app.agent.utils.sanitizers import normalize_obfuscated_numbers
from app.agent.llm import call_llm
from app.core.rules import (
    UPI_PATTERN,
    PHONE_PATTERN,
    LINK_PATTERN,
    BANK_ACCOUNT_PATTERN,
    EMAIL_DOMAINS_TO_EXCLUDE,
    SUSPECTED_SCAM_KEYWORDS,
    EXTRACT_SYSTEM_PROMPT,
    STAFF_ID_PATTERN,
    EMAIL_PATTERN,
    CASE_ID_PATTERN,
    ORDER_NUMBER_PATTERN,
    POLICY_NUMBER_PATTERN,
)



def _clean_item(text: str) -> str:
    """Strip trailing punctuation used in sentences (.,!?;:)]})."""
    if not text:
        return text
    # Common trailing noise in chat messages
    return text.rstrip('.,!?;:)]}').strip()


def _extract_upi_ids(text: str) -> List[str]:
    """Extract UPI IDs from text using regex."""
    matches = UPI_PATTERN.findall(text)
    upis = [m for m in matches if m.split('@')[1].lower() not in EMAIL_DOMAINS_TO_EXCLUDE]
    return [_clean_item(u) for u in upis]


def _extract_phone_numbers(text: str) -> List[str]:
    """Extract Indian phone numbers from text using regex."""
    matches = PHONE_PATTERN.findall(text)
    normalized = []
    for m in matches:
        clean = re.sub(r'[\s-]', '', m)
        if clean.startswith('+'):
            clean = clean[1:]
        if clean.startswith('91') and len(clean) == 12:
            clean = clean[2:]
        if len(clean) == 10:
            normalized.append(clean)
        # Also preserve original match for benchmark consistency (+91- prefix etc)
        normalized.append(m.strip())
    return normalized


def _extract_links(text: str) -> List[str]:
    """Extract phishing links from text using regex."""
    matches = LINK_PATTERN.findall(text)
    return [_clean_item(m) for m in matches]


def _extract_emails(text: str) -> List[str]:
    """Extract email addresses from text using regex."""
    matches = EMAIL_PATTERN.findall(text)
    return [_clean_item(m) for m in matches]


def _extract_bank_accounts(text: str) -> List[str]:
    """Extract potential bank account numbers from text using regex."""
    matches = BANK_ACCOUNT_PATTERN.findall(text)
    accounts = []
    for m in matches:
        # 1. Skip if it's strictly a 10-digit Indian mobile (starts 6-9)
        if len(m) == 10 and m[0] in '6789':
            continue
            
        # 2. Skip if it's a 12-digit Indian mobile with '91' prefix
        if len(m) == 12 and m.startswith('91') and m[2] in '6789':
            continue
            
        # 3. Skip if it's an 11-digit mobile with '0' prefix (Indian landline/mobile standard)
        if len(m) == 11 and m.startswith('0') and m[1] in '6789':
            continue

        # Only include numbers that are likely bank accounts (usually >= 9 digits)
        if len(m) >= 9:
            accounts.append(m)
    return accounts


def _extract_staff_ids(text: str) -> List[str]:
    """Extract staff IDs using regex."""
    return [m.strip() for m in STAFF_ID_PATTERN.findall(text)]


def _extract_ifsc_codes(text: str) -> List[str]:
    """Extract IFSC codes (bank branch identifiers) using regex."""
    from app.core.rules import IFSC_PATTERN
    return IFSC_PATTERN.findall(text)


def _extract_pan_numbers(text: str) -> List[str]:
    """Extract PAN numbers (tax IDs) using regex."""
    from app.core.rules import PAN_PATTERN
    return PAN_PATTERN.findall(text)


def _extract_sebi_handles(text: str) -> List[str]:
    """Extract SEBI @valid handles (investment scam identifiers) using regex."""
    from app.core.rules import SEBI_HANDLE_PATTERN
    return SEBI_HANDLE_PATTERN.findall(text)

def _flatten_matches(matches: List[Any]) -> List[str]:
    flat = []
    for m in matches:
        if isinstance(m, tuple):
            flat.extend([x.strip() for x in m if x.strip()])
        else:
            flat.append(m.strip())
    return flat

def _extract_policy_numbers(text: str) -> List[str]:
    return _flatten_matches(POLICY_NUMBER_PATTERN.findall(text))

def _extract_order_numbers(text: str) -> List[str]:
    return _flatten_matches(ORDER_NUMBER_PATTERN.findall(text))

def _extract_case_ids(text: str) -> List[str]:
    return _flatten_matches(CASE_ID_PATTERN.findall(text))



# Local normalization replaced by app.agent.utils.sanitizers.normalize_obfuscated_numbers


def _extract_suspicious_keywords(text: str) -> List[str]:
    """Extract suspicious keywords found in the text."""
    text_lower = text.lower()
    found = []
    for keyword in SUSPECTED_SCAM_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)
    return found


def _parse_llm_extraction(response: str) -> Dict[str, Any]:
    """Parse LLM JSON response for extracted data."""
    result = {
        "upiIds": [], 
        "phoneNumbers": [], 
        "phishingLinks": [], 
        "bankAccounts": [],
        "scammerNames": [],
        "staffIds": [],
        "emailAddresses": [],
        "caseIds": [],
        "orderNumbers": [],
        "policyNumbers": [],
        "agentNotes": "",
    }
    
    # Try to find JSON in response
    try:
        # Handle markdown code blocks
        if "```" in response:
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
        
        data = json.loads(response.strip())
        
        if isinstance(data.get("upiIds"), list):
            result["upiIds"] = [_clean_item(str(x)) for x in data["upiIds"] if x]
        if isinstance(data.get("phoneNumbers"), list):
            result["phoneNumbers"] = [_clean_item(str(x)) for x in data["phoneNumbers"] if x]
        if isinstance(data.get("phishingLinks"), list):
            result["phishingLinks"] = [_clean_item(str(x)) for x in data["phishingLinks"] if x]
        if isinstance(data.get("bankAccounts"), list):
            result["bankAccounts"] = [_clean_item(str(x)) for x in data["bankAccounts"] if x]
        if isinstance(data.get("scammerNames"), list):
            result["scammerNames"] = [_clean_item(str(x)) for x in data["scammerNames"] if x]
        if isinstance(data.get("staffIds"), list):
            result["staffIds"] = [_clean_item(str(x)) for x in data["staffIds"] if x]
        if isinstance(data.get("emailAddresses"), list):
            result["emailAddresses"] = [_clean_item(str(x)) for x in data["emailAddresses"] if x]
        if isinstance(data.get("caseIds"), list):
            result["caseIds"] = [_clean_item(str(x)) for x in data["caseIds"] if x]
        if isinstance(data.get("orderNumbers"), list):
            result["orderNumbers"] = [_clean_item(str(x)) for x in data["orderNumbers"] if x]
        if isinstance(data.get("policyNumbers"), list):
            result["policyNumbers"] = [_clean_item(str(x)) for x in data["policyNumbers"] if x]
        if isinstance(data.get("agentNotes"), str):
            result["agentNotes"] = _clean_item(data["agentNotes"])
            
    except (json.JSONDecodeError, AttributeError):
        pass
    
    return result


async def extractor_node(state: AgentState) -> Dict[str, Any]:
    """
    Extractor node: Extracts intelligence using regex + optional LLM reinforcement.
    Now FULLY ASYNCHRONOUS.
    """
    t_start = time.perf_counter()
    llm_duration_ms = 0.0
    
    message = state["current_user_message"]
    messages = state.get("messages", [])
    
    # PREPROCESSING: 2025 Standard De-obfuscation
    message_normalized = normalize_obfuscated_numbers(message)
    
    # Step 1: Regex extraction (deterministic)
    # Run on both raw and normalized to ensure literal matches (benchmark) and obfuscated (real-world)
    regex_upi_raw = _extract_upi_ids(message)
    regex_upi_norm = _extract_upi_ids(message_normalized)
    regex_upi = list(set(regex_upi_raw) | set(regex_upi_norm))
    
    regex_phones_raw = _extract_phone_numbers(message)
    regex_phones_norm = _extract_phone_numbers(message_normalized)
    regex_phones = list(set(regex_phones_raw) | set(regex_phones_norm))
    
    regex_links_raw = _extract_links(message)
    regex_links_norm = _extract_links(message_normalized)
    regex_links = list(set(regex_links_raw) | set(regex_links_norm))
    
    regex_accounts_raw = _extract_bank_accounts(message)
    regex_accounts_norm = _extract_bank_accounts(message_normalized)
    regex_accounts = list(set(regex_accounts_raw) | set(regex_accounts_norm))
    
    regex_staff = list(set(_extract_staff_ids(message)) | set(_extract_staff_ids(message_normalized)))
    regex_emails = list(set(_extract_emails(message)) | set(_extract_emails(message_normalized)))
    regex_keywords = list(set(_extract_suspicious_keywords(message)) | set(_extract_suspicious_keywords(message_normalized)))
    regex_ifsc = list(set(_extract_ifsc_codes(message)) | set(_extract_ifsc_codes(message_normalized)))
    regex_pan = list(set(_extract_pan_numbers(message)) | set(_extract_pan_numbers(message_normalized)))
    regex_sebi = list(set(_extract_sebi_handles(message)) | set(_extract_sebi_handles(message_normalized)))
    
    # Step 2: LLM reinforcement
    llm_upi = []
    llm_phones = []
    llm_links = []
    llm_accounts = []
    llm_names = []
    llm_staff = []
    llm_emails = []
    llm_case_ids = []
    llm_order_nums = []
    llm_policy_nums = []
    llm_agent_notes = ""
    
    from app.config import get_settings
    settings = get_settings()
    needs_llm = settings.FLAG_LLM_EXTRACTION and len(message) > 15
    
    if needs_llm:
        context = f"Message: {message}"
        if messages:
            scammer_texts = [m.get("text", "") for m in messages if str(m.get("sender", "")).lower() == "scammer"]
            if scammer_texts:
                context += f"\n\nContext: {' | '.join(scammer_texts[-3:])}"
        
        llm_messages = [{"role": "system", "content": EXTRACT_SYSTEM_PROMPT}, {"role": "user", "content": context}]
        
        t_llm_start = time.perf_counter()
        llm_response = await call_llm("extract", llm_messages)
        llm_duration_ms = round((time.perf_counter() - t_llm_start) * 1000, 1)
        llm_data = _parse_llm_extraction(llm_response)
        
        llm_upi = llm_data["upiIds"]
        llm_phones = llm_data["phoneNumbers"]
        llm_links = llm_data["phishingLinks"]
        llm_accounts = llm_data["bankAccounts"]
        llm_names = llm_data["scammerNames"]
        llm_staff = llm_data["staffIds"]
        llm_emails = llm_data.get("emailAddresses", [])
        llm_case_ids = llm_data.get("caseIds", [])
        llm_order_nums = llm_data.get("orderNumbers", [])
        llm_policy_nums = llm_data.get("policyNumbers", [])
        llm_agent_notes = llm_data.get("agentNotes", "")
    
    # Step 3: Identity Filtering (Podium Hardening)
    # Filter out our own fake bait data so it's not reported as scammer intelligence
    p_name = state.get("persona_name", "").lower()
    fake_vals = {
        state.get("fake_phone", ""),
        state.get("fake_upi", ""),
        state.get("fake_bank_account", ""),
        state.get("fake_ifsc", ""),
        # Also filter out simple derivations
        p_name
    }
    fake_vals = {str(v).lower().strip() for v in fake_vals if v}

    all_upi = [u for u in (set(regex_upi) | set(llm_upi)) if u.lower().strip() not in fake_vals]
    all_phones = [p for p in (set(regex_phones) | set(llm_phones)) if p.lower().strip() not in fake_vals]
    all_links = [l for l in (set(regex_links) | set(llm_links)) if l.lower().strip() not in fake_vals]
    
    # Priority Filtering: If something is a phone number, it's NOT a bank account.
    # We strip 91/0 from all_phones to check against bank accounts (which might be raw digits)
    phone_stubs = {p[-10:] for p in all_phones}
    all_accounts = []
    for a in (set(regex_accounts) | set(llm_accounts)):
        val = a.lower().strip()
        if val in fake_vals:
            continue
        # If the account number ends with a known phone number and is 10-12 digits, skip it
        if len(val) <= 12 and val[-10:] in phone_stubs:
            continue
        all_accounts.append(a)

    all_emails = [e for e in (set(regex_emails) | set(llm_emails)) if e.lower().strip() not in fake_vals]
    
    all_keywords = list(set(regex_keywords))
    found_names = [n for n in set(llm_names) if n.lower().strip() not in fake_vals and len(n) > 2]
    found_staff = [s for s in (set(regex_staff) | set(llm_staff)) if s.lower().strip() not in fake_vals]
    found_ifsc = [i for i in set(regex_ifsc) if i.lower().strip() not in fake_vals]
    found_pan = list(set(regex_pan))
    found_sebi = list(set(regex_sebi))
    
    # Step 4: Merge with existing
    existing = state.get("extracted_intelligence", {})
    if hasattr(existing, "model_dump"):
        existing = existing.model_dump()

    merged_intel = {
        "upiIds": list(set(existing.get("upiIds", [])) | set(all_upi)),
        "phoneNumbers": list(set(existing.get("phoneNumbers", [])) | set(all_phones)),
        "phishingLinks": list(set(existing.get("phishingLinks", [])) | set(all_links)),
        "bankAccounts": list(set(existing.get("bankAccounts", [])) | set(all_accounts)),
        "suspiciousKeywords": list(set(existing.get("suspiciousKeywords", [])) | set(all_keywords)),
        "scammerNames": list(set(existing.get("scammerNames", [])) | set(found_names)),
        "staffIds": list(set(existing.get("staffIds", [])) | set(found_staff)),
        "emailAddresses": list(set(existing.get("emailAddresses", [])) | set(all_emails)),
        "ifscCodes": list(set(existing.get("ifscCodes", [])) | set(found_ifsc)),
        "panNumbers": list(set(existing.get("panNumbers", [])) | set(found_pan)),
        "sebiHandles": list(set(existing.get("sebiHandles", [])) | set(found_sebi)),
    }
    
    # Step 5: Notes
    notes = state.get("agent_notes", "")
    new_notes = []
    if found_names:
        new_names = [n for n in found_names if n.lower() not in notes.lower()]
        if new_names: new_notes.append(f"Scammer name: {', '.join(new_names)}")
    if found_staff:
        new_ids = [i for i in found_staff if i.lower() not in notes.lower()]
        if new_ids: new_notes.append(f"Staff ID: {', '.join(new_ids)}")
            
    if new_notes:
        notes = (notes + "\n" if notes else "") + "\n".join(new_notes)
    
    # Determine if scam is confirmed
    # Critical intel: presence of these likely confirms a scam
    # Added phoneNumbers and emails to help detection in scenarios where links/upi are missed
    has_critical_intel = bool(
        merged_intel["upiIds"] or 
        merged_intel["bankAccounts"] or 
        merged_intel["phishingLinks"] or
        merged_intel["phoneNumbers"] or
        merged_intel["emailAddresses"]
    )
    
    
    # 6. Extract Extended Intel (Case IDs, Order Numbers, Policy Numbers)
    regex_case_ids = list(set(_extract_case_ids(message)) | set(_extract_case_ids(message_normalized)))
    regex_order_nums = list(set(_extract_order_numbers(message)) | set(_extract_order_numbers(message_normalized)))
    regex_policy_nums = list(set(_extract_policy_numbers(message)) | set(_extract_policy_numbers(message_normalized)))
    
    all_case_ids = list(set(regex_case_ids) | set(llm_case_ids))
    all_order_nums = list(set(regex_order_nums) | set(llm_order_nums))
    all_policy_nums = list(set(regex_policy_nums) | set(llm_policy_nums))
    
    merged_intel["caseIds"] = list(set(existing.get("caseIds", [])) | set(all_case_ids))
    merged_intel["orderNumbers"] = list(set(existing.get("orderNumbers", [])) | set(all_order_nums))
    merged_intel["policyNumbers"] = list(set(existing.get("policyNumbers", [])) | set(all_policy_nums))
    
    extra_notes = []
    if all_case_ids: extra_notes.append(f"Case IDs: {', '.join(all_case_ids)}")
    if all_order_nums: extra_notes.append(f"Order Numbers: {', '.join(all_order_nums)}")
    if all_policy_nums: extra_notes.append(f"Policy Numbers: {', '.join(all_policy_nums)}")
    
    if extra_notes:
        existing_notes = merged_intel.get("agent_notes", "") # use existing if any
        notes = (notes + "\n" + "\n".join(extra_notes)).strip()
        
    # Append any dynamic agentNotes found by the LLM
    if llm_agent_notes:
        notes = (notes + "\n" + llm_agent_notes).strip()

    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)
    
    result = {
        "extracted_intelligence": merged_intel,
        "is_scam_confirmed": state.get("is_scam_confirmed", False) or has_critical_intel,
        "agent_notes": notes,
    }


    duration_ms = round((time.perf_counter() - t_start) * 1000, 1)

    timing_entry = {"node": "extractor", "duration_ms": duration_ms}
    if llm_duration_ms: timing_entry["llm_ms"] = llm_duration_ms
    
    result = {
        "extracted_intelligence": merged_intel,
        "agent_notes": notes,
        "timing_log": [timing_entry],
    }
    if has_critical_intel:
        result["is_scam_confirmed"] = True
        result["scam_level"] = "confirmed"
    return result
