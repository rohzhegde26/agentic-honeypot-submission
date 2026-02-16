"""
Pydantic model for session state stored in Redis.
Matches the LangGraph AgentState schema from 07_LangGraph_State_Schema.md
"""
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from .callback import ExtractedIntelligence


class SessionData(BaseModel):
    """
    Session state persisted in Redis.
    Designed to be < 1KB when serialized for Upstash free tier limits.
    """
    # Session Identifiers
    session_id: str = Field(..., description="Unique session ID")
    
    # Message Flow (store minimal data to keep size < 1KB)
    messages: List[Dict] = Field(default_factory=list, description="Conversation log")
    current_user_message: str = Field(default="", description="Latest message")
    
    # Analysis State
    scam_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    is_scam_confirmed: bool = Field(default=False, description="Hard confirmation flag")
    scam_level: Literal["safe", "suspected", "confirmed"] = Field(
        default="safe",
        description="Current scam detection level"
    )
    
    # Extracted Intel
    extracted_intelligence: ExtractedIntelligence = Field(
        default_factory=ExtractedIntelligence,
        description="Extracted scammer data"
    )
    
    # Control Flow
    turn_count: int = Field(default=0, description="Number of turns in conversation")
    intel_found_at_turn: Optional[int] = Field(default=None, description="Turn number when intel was first found")
    termination_reason: Optional[str] = Field(
        default=None,
        description="Why conversation ended: max_turns, extracted_success, user_quit"
    )
    agent_notes: str = Field(default="", description="Agent observations")
    
    # Persona tracking for consistency
    persona_name: str = Field(default="", description="Current persona's name")
    persona_age: int = Field(default=0, description="Current persona's age")
    persona_location: str = Field(default="", description="Current persona's location")
    persona_background: str = Field(default="", description="Current persona's background")
    persona_occupation: str = Field(default="", description="Current persona's occupation")
    persona_trait: str = Field(default="", description="Current persona's trait")
    
    # Fake details generated for this session
    fake_phone: str = Field(default="", description="Fake 10-digit Indian phone number")
    fake_upi: str = Field(default="", description="Fake UPI ID")
    fake_bank_account: str = Field(default="", description="Fake bank account number")
    fake_ifsc: str = Field(default="", description="Fake IFSC code")
    
    # Callback tracking
    callback_sent: bool = Field(default=False, description="Whether final callback was sent")
