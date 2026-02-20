"""
Extracted Intelligence Scorer — 30 Points.
Black-box: compares extractedIntelligence against planted fake data.

Rubric:
  Points per item = 30 ÷ total fake data fields in scenario
  Each correctly extracted field earns points_per_item.
"""
import re
from typing import Dict, Any, List
from evaluation.api_client import APIResponse
from evaluation.config import FakeData


def _normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison (strip spaces, dashes, +91 prefix)."""
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone)
    # Remove country code variants
    for prefix in ["+91", "91", "0091"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    url = url.strip().lower()
    # Remove trailing slash
    url = url.rstrip("/")
    # Remove protocol for comparison
    for prefix in ["https://", "http://"]:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url


def _normalize_string(s: str) -> str:
    """Generic normalization — lowercase, strip whitespace."""
    return s.strip().lower()


def _fuzzy_match(expected: str, extracted_list: List[str], normalizer) -> bool:
    """Check if expected value exists in extracted list using normalizer."""
    norm_expected = normalizer(expected)
    for item in extracted_list:
        if normalizer(item) == norm_expected:
            return True
        # Also check if expected is a substring (for partial matches)
        if norm_expected in normalizer(item) or normalizer(item) in norm_expected:
            return True
    return False


# Map fake data field names to intelligence response field names and normalizers
FIELD_MAP = {
    "phoneNumbers": ("phoneNumbers", _normalize_phone),
    "bankAccounts": ("bankAccounts", _normalize_string),
    "upiIds": ("upiIds", _normalize_string),
    "phishingLinks": ("phishingLinks", _normalize_url),
    "emailAddresses": ("emailAddresses", _normalize_string),
    "caseIds": ("caseIds", _normalize_string),
    "policyNumbers": ("policyNumbers", _normalize_string),
    "orderNumbers": ("orderNumbers", _normalize_string),
}


def score_intelligence_extraction(
    responses: List[APIResponse],
    fake_data: FakeData,
) -> Dict[str, Any]:
    """
    Score intelligence extraction against planted fake data.
    
    Returns:
        Dict with score, max_score, details, and losses.
    """
    max_score = 30
    losses = []

    total_fake_fields = fake_data.total_fields()

    if total_fake_fields == 0:
        return {
            "score": 30,
            "max_score": max_score,
            "details": "No fake data planted in scenario — full marks by default.",
            "losses": [],
        }

    points_per_item = 30.0 / total_fake_fields

    if not responses:
        return {
            "score": 0,
            "max_score": max_score,
            "details": "No responses received.",
            "losses": [{"points_lost": 30, "reason": "No API responses — could not evaluate intelligence extraction."}],
        }

    # Use the LAST response's extractedIntelligence (cumulative)
    final_intel = responses[-1].extracted_intelligence or {}

    extracted_count = 0
    missed_items = []
    found_items = []
    details_lines = []

    fake_dict = fake_data.as_dict()

    for field_name, expected_values in fake_dict.items():
        response_field, normalizer = FIELD_MAP.get(field_name, (field_name, _normalize_string))
        extracted_values = final_intel.get(response_field, [])

        if isinstance(extracted_values, str):
            extracted_values = [extracted_values] if extracted_values else []

        for expected_val in expected_values:
            if _fuzzy_match(expected_val, extracted_values, normalizer):
                extracted_count += 1
                found_items.append(f"  ✅ {field_name}: '{expected_val}' — found")
            else:
                missed_items.append(f"  ❌ {field_name}: '{expected_val}' — NOT found")
                losses.append({
                    "points_lost": round(points_per_item, 2),
                    "reason": f"Failed to extract {field_name} value '{expected_val}' from the conversation. "
                              f"The scammer mentioned this in the conversation, but it was not in extractedIntelligence.{response_field}.",
                })

    score = round(min(extracted_count * points_per_item, 30), 2)

    details = (
        f"Extracted {extracted_count}/{total_fake_fields} planted data items.\n"
        f"Points per item: {points_per_item:.2f}\n"
    )
    if found_items:
        details += "\nFound:\n" + "\n".join(found_items)
    if missed_items:
        details += "\n\nMissed:\n" + "\n".join(missed_items)

    return {
        "score": score,
        "max_score": max_score,
        "details": details,
        "losses": losses,
    }
