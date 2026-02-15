"""
Parallel Execution Node.
Runs extractor and persona nodes concurrently via asyncio.gather
to eliminate the serial latency of extractor → persona.

Data dependency proof:
  - extractor reads: current_user_message, messages, extracted_intelligence (existing)
  - persona reads: current_user_message, messages, scam_level, persona_*, fake_*
  - NO bilateral dependency — they read/write completely different state keys.

Merge strategy:
  - timing_log: concatenated (both entries preserved)
  - messages: from persona only (extractor never writes messages)
  - agent_notes: persona "BLOCKED" notes take priority over extractor's notes
  - extracted_intelligence, is_scam_confirmed: from extractor only
  - agent_reply: from persona only
"""
import asyncio
import logging
from typing import Dict, Any

from app.agent.state import AgentState
from app.agent.nodes.extractor import extractor_node
from app.agent.nodes.persona import persona_node

logger = logging.getLogger(__name__)


async def extract_and_respond(state: AgentState) -> Dict[str, Any]:
    """
    Combined node: runs extractor and persona in parallel.
    
    Returns merged result with explicit merge priority:
    - Intel fields (extracted_intelligence, is_scam_confirmed) from extractor
    - Reply fields (agent_reply, messages) from persona
    - agent_notes: persona's "BLOCKED" notes override extractor's notes
    - timing_log: concatenated from both nodes
    """
    # Run both nodes concurrently (now natively async)
    extractor_result, persona_result = await asyncio.gather(
        extractor_node(state),
        persona_node(state),
    )
    
    # =========================================================================
    # Explicit Merge Logic
    # =========================================================================
    merged: Dict[str, Any] = {}
    
    # From extractor: intelligence data
    if "extracted_intelligence" in extractor_result:
        merged["extracted_intelligence"] = extractor_result["extracted_intelligence"]
    if "is_scam_confirmed" in extractor_result:
        merged["is_scam_confirmed"] = extractor_result["is_scam_confirmed"]
    
    # From persona: reply and message history
    merged["agent_reply"] = persona_result.get("agent_reply", "")
    if "messages" in persona_result:
        merged["messages"] = persona_result["messages"]
    
    # agent_notes merge: persona "BLOCKED" takes priority
    extractor_notes = extractor_result.get("agent_notes", "")
    persona_notes = persona_result.get("agent_notes", "")
    
    if persona_notes and "BLOCKED" in persona_notes:
        # Persona blocked the input — its notes take priority
        merged["agent_notes"] = persona_notes
        logger.info(f"Parallel merge: persona BLOCKED, using persona notes")
    elif extractor_notes and persona_notes:
        # Both have notes, combine them
        merged["agent_notes"] = f"{extractor_notes}\n{persona_notes}"
    elif extractor_notes:
        merged["agent_notes"] = extractor_notes
    elif persona_notes:
        merged["agent_notes"] = persona_notes
    
    # timing_log: concatenate both (operator.add reducer handles this in state)
    extractor_timing = extractor_result.get("timing_log", [])
    persona_timing = persona_result.get("timing_log", [])
    merged["timing_log"] = extractor_timing + persona_timing
    
    logger.info(
        f"Parallel execution complete: "
        f"extractor={extractor_timing[0].get('duration_ms', 0) if extractor_timing else 0}ms, "
        f"persona={persona_timing[0].get('duration_ms', 0) if persona_timing else 0}ms"
    )
    
    return merged
