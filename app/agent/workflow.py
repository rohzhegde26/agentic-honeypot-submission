"""
LangGraph Workflow Definition.
Orchestrates the Detect -> Extract -> Engage flow with conditional routing.
"""
import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END

from app.config import get_settings
from app.agent.state import AgentState
from app.agent.nodes.detector import detector_node
from app.agent.nodes.extractor import extractor_node
from app.agent.nodes.persona import persona_node
from app.agent.nodes.output import output_node
from app.agent.nodes.parallel import extract_and_respond

logger = logging.getLogger(__name__)


def route_after_detection(state: AgentState) -> Literal["extractor", "output"]:
    """
    Conditional edge: Route based on scam detection result.
    
    - If suspected/confirmed: Always go to extractor_node (extract intel)
    - If safe AND turn_count <= 1: Go to output_node (skip extraction)
    - If safe AND turn_count > 1: Go to extractor_node (still extract)
    """
    scam_level = state.get("scam_level", "safe")
    turn_count = state.get("turn_count", 0)
    
    # Always extract for suspected/confirmed scams (regardless of turn count)
    # This ensures we capture UPI IDs, bank accounts, phone numbers from scam messages
    if scam_level in ["suspected", "confirmed"]:
        logger.info(f"Routing to EXTRACTOR (scam_level={scam_level}, turn={turn_count})")
        return "extractor"
    
    # For safe messages: only skip extraction on first turn to save resources
    if scam_level == "safe" and turn_count <= 1:
        logger.info("Routing to OUTPUT (safe message, initial turn, no extraction)")
        return "output"
    else:
        # Safe message but in ongoing conversation OR turn > 1: still extract
        logger.info(f"Routing to EXTRACTOR (scam_level={scam_level}, turn={turn_count})")
        return "extractor"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow.
    
    Flow:
    1. Start -> detector_node
    2. detector_node -> (safe first turn -> output_node)
                      | (all other -> extract_and_respond)
    3. extract_and_respond -> output_node  [runs extractor + persona in parallel]
    4. output_node -> End
    
    Node Responsibilities:
    - detector_node: Sets scam_level only
    - extract_and_respond: Runs extractor + persona concurrently,
      merges results (intel from extractor, reply from persona)
    - output_node: Returns reply and updates turn_count
    """
    # Create graph with AgentState
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("detector", detector_node)
    graph.add_node("extract_and_respond", extract_and_respond)
    graph.add_node("output", output_node)
    
    # Set entry point
    graph.set_entry_point("detector")
    
    # Add conditional edge from detector
    graph.add_conditional_edges(
        "detector",
        route_after_detection,
        {
            "extractor": "extract_and_respond",
            "output": "output",
        }
    )
    
    # Parallel node -> Output
    graph.add_edge("extract_and_respond", "output")
    
    # Output always ends
    graph.add_edge("output", END)
    
    return graph


# Compile the graph once
_compiled_graph = None


def get_compiled_graph():
    """Get the compiled graph (lazy initialization)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = create_agent_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph


async def run_agent(
    session_id: str,
    message: str,
    messages_history: list,
    metadata: Dict[str, str],
    turn_count: int = 1,
    existing_intel: Dict = None,
    intel_found_at_turn: int = None,
    persona_details: Dict = None,  # Existing persona if any
    simulated_elapsed_time: float = 0.0,
) -> Dict[str, Any]:
    """
    Run the agent workflow for a single turn.
    """
    logger.info(f"Running agent for session {session_id}, turn {turn_count}")
    
    # Get settings for persona configuration
    settings = get_settings()
    
    # Initialize persona and fake details
    if not persona_details or not persona_details.get("persona_name"):
        import random
        from app.agent.utils.generators import (
            generate_phone_number,
            generate_upi_id,
            generate_bank_account,
            generate_ifsc
        )
        
        # Pick a random template
        template = random.choice(settings.PERSONA_TEMPLATES)
        p_name = template["name"]
        p_age = template["age"]
        p_location = template["location"]
        p_background = template["background"]
        p_occupation = template["occupation"]
        p_trait = template["trait"]
        
        # Generate fake data
        f_phone = generate_phone_number()
        f_upi = generate_upi_id(p_name)
        f_bank = generate_bank_account()
        f_ifsc = generate_ifsc()
    else:
        p_name = persona_details.get("persona_name")
        p_age = persona_details.get("persona_age")
        p_location = persona_details.get("persona_location")
        p_background = persona_details.get("persona_background")
        p_occupation = persona_details.get("persona_occupation")
        p_trait = persona_details.get("persona_trait")
        f_phone = persona_details.get("fake_phone")
        f_upi = persona_details.get("fake_upi")
        f_bank = persona_details.get("fake_bank_account")
        f_ifsc = persona_details.get("fake_ifsc")

    # Initialize state
    initial_state: AgentState = {
        "session_id": session_id,
        "current_user_message": message,
        "messages": messages_history or [],
        "scam_confidence": 0.0,
        "is_scam_confirmed": False,
        "scam_level": "safe",
        "extracted_intelligence": existing_intel or {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": [],
            "scammerNames": [],
            "staffIds": [],
            "emailAddresses": [],
            "ifscCodes": [],
            "panNumbers": [],
            "sebiHandles": [],
        },
        "turn_count": turn_count,
        "intel_found_at_turn": intel_found_at_turn,
        "termination_reason": None,
        "agent_notes": "",
        "agent_reply": "",
        "persona_name": p_name,
        "persona_age": p_age,
        "persona_location": p_location,
        "persona_background": p_background,
        "persona_occupation": p_occupation,
        "persona_trait": p_trait,
        "fake_phone": f_phone,
        "fake_upi": f_upi,
        "fake_bank_account": f_bank,
        "fake_ifsc": f_ifsc,
        "channel": metadata.get("channel", "SMS"),
        "language": metadata.get("language", "en"),
        "locale": metadata.get("locale", "IN"),
        "simulated_elapsed_time": simulated_elapsed_time,
        "timing_log": [],
    }
    
    # Run the graph
    graph = get_compiled_graph()
    result = await graph.ainvoke(initial_state)
    
    # Ensure we have a reply
    if not result.get("agent_reply"):
        result["agent_reply"] = "Hello, I think there is some confusion. Who is this?"
    
    logger.info(f"Agent completed. Reply: {result['agent_reply'][:50]}...")
    
    return result
