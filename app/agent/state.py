"""
LangGraph Agent State Definition.
Matches 07_LangGraph_State_Schema.md specification.
"""
from typing import List, Dict, Optional, Literal, Annotated, TypedDict
import operator


class ExtractedData(TypedDict):
    """Intelligence extracted from scammer."""
    bankAccounts: List[str]
    upiIds: List[str]
    phishingLinks: List[str]
    phoneNumbers: List[str]
    suspiciousKeywords: List[str]
    scammerNames: List[str]
    staffIds: List[str]
    emailAddresses: List[str]
    ifscCodes: List[str]
    panNumbers: List[str]
    sebiHandles: List[str]


class AgentState(TypedDict):
    """
    State passed between LangGraph nodes.
    This is the central data structure for the agent workflow.
    """
    # Session Identifiers
    session_id: str
    
    # Message Flow
    messages: Annotated[List[Dict], operator.add]  # Append-only log
    current_user_message: str
    
    # Analysis State
    scam_confidence: float  # 0.0 to 1.0
    is_scam_confirmed: bool
    scam_level: Literal["safe", "suspected", "confirmed"]
    
    # Extracted Intel
    extracted_intelligence: ExtractedData
    
    # Control Flow
    turn_count: int
    intel_found_at_turn: Optional[int]
    termination_reason: Optional[str]  # "max_turns", "extracted_success", "user_quit"
    agent_notes: str
    
    # Agent Reply (set by persona node)
    agent_reply: str
    
    # Persona Tracking
    persona_name: str
    persona_age: int
    persona_location: str
    persona_background: str
    persona_occupation: str
    persona_trait: str
    
    # Fake details for baiting
    fake_phone: str
    fake_upi: str
    fake_bank_account: str
    fake_ifsc: str
    
    # Metadata
    channel: str
    language: str
    locale: str
    
    # Timing instrumentation (appended by each node)
    timing_log: Annotated[List[Dict], operator.add]
