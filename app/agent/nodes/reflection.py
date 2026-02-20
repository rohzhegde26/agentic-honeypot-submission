"""
Reflection Node for Self-Correction.
Runs in the background to analyze conversation effectiveness and adapt persona strategy.
"""
import logging
import json
import re
from typing import Dict, Any

from app.agent.llm import call_llm
from app.core.rules import REFLECTION_SYSTEM_PROMPT
from app.schemas.session import SessionData

logger = logging.getLogger(__name__)


def _clean_llm_json(text: str) -> str:
    """
    Robustly pre-processes an LLM response to extract clean JSON.
    Handles:
    - Markdown fences (```json ... ``` or ``` ... ```)
    - JS-style inline comments (// ...)
    - Trailing commas before } or ] (invalid in strict JSON)
    Returns the cleaned string ready for json.loads().
    """
    # 1. Strip markdown fences
    fenced = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    # 2. Extract the outermost JSON object
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]
    else:
        return text.strip()

    # 3. Remove JS-style inline comments
    text = re.sub(r'//[^\n]*', '', text)

    # 4. Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    return text.strip()

async def run_reflection(session: SessionData) -> Dict[str, Any]:
    """
    Analyzes the session and generates a strategic reflection.
    Returns a dict with updates for the session.
    """
    try:
        # Prepare intel summary
        intel = session.extracted_intelligence
        intel_summary = f"UPIs: {len(intel.upiIds)}, Banks: {len(intel.bankAccounts)}, Links: {len(intel.phishingLinks)}"
        
        # Build prompt
        prompt = REFLECTION_SYSTEM_PROMPT.format(
            persona_name=session.persona_name,
            persona_trait=session.persona_trait,
            turn_count=session.turn_count,
            intel_summary=intel_summary
        )
        
        # Collapse history into a single string to avoid "Last message must be User" error in Mistral
        history_str = ""
        for m in session.messages[-6:]:
            sender = "Agent" if m["sender"] == "agent" else "User"
            history_str += f"{sender}: {m['text']}\n"
            
        full_content = f"{prompt}\n\nRecent Conversation:\n{history_str}\n\nAnalyze the interaction."
        
        # Send as single User message
        llm_messages = [{"role": "user", "content": full_content}]
        response_text = await call_llm("reflection", llm_messages)
        
        try:
            # Parse JSON with robust pre-processing
            clean_json = _clean_llm_json(response_text)

            try:
                data = json.loads(clean_json)
                logger.info(f"Reflection completed for session {session.session_id}: {data.get('reflection')}")
                return data
            except Exception as e:
                logger.error(f"JSON load failed after cleaning: {e}")

            # 2. Fallback: Try to parse conversational output
            logger.warning("Attempting conversational fallback for reflection")
            data = {}
            if "suggested_trait" in clean_json.lower() or "trait" in clean_json.lower():
                # Simple heuristic extraction
                trait_match = re.search(r'trait["\s:]+([^"\n,]+)', clean_json, re.I)
                if trait_match:
                    data["suggested_trait"] = trait_match.group(1).strip().strip('"').strip("'")
            
            if data.get("suggested_trait"):
                data["reflection"] = "Conversational analysis extracted."
                data["internal_thoughts"] = clean_json[:200]
                return data

            # 3. FAILURE Log
            print(f"DEBUG: Response len: {len(clean_json)}")
            print(f"RAW: {clean_json[:500]}")
            logger.error(f"FAILURE: No JSON or valid trait found in response.")
            return {}
            
        except Exception as e:
            logger.error(f"Reflection parse error: {e}")
            return {}
            
    except Exception as e:
        logger.error(f"Reflection error: {e}")
        return {}
