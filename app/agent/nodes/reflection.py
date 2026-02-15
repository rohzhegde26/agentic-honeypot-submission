"""
Reflection Node for Self-Correction.
Runs in the background to analyze conversation effectiveness and adapt persona strategy.
"""
import logging
import json
from typing import Dict, Any

from app.agent.llm import call_llm
from app.core.rules import REFLECTION_SYSTEM_PROMPT
from app.schemas.session import SessionData

logger = logging.getLogger(__name__)

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
        
        # We only need the last few messages for context
        messages = session.messages[-6:]
        llm_messages = [{"role": "system", "content": prompt}]
        for m in messages:
            role = "assistant" if m["sender"] == "agent" else "user"
            llm_messages.append({"role": role, "content": m["text"]})
            
        # Call LLM
        response_text = call_llm("reflection", llm_messages)
        
        try:
            # Parse JSON with robust extraction
            clean_json = response_text.strip()
            
            # 1. Try to find the first '{' and last '}'
            start_idx = clean_json.find('{')
            end_idx = clean_json.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_json[start_idx:end_idx+1]
                try:
                    data = json.loads(json_str)
                    logger.info(f"Reflection completed for session {session.session_id}: {data.get('reflection')}")
                    return data
                except Exception as e:
                    logger.error(f"JSON load failed on extracted str: {e}")
            
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
