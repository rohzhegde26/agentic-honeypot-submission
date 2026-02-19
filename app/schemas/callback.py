"""
Pydantic models for the final callback payload.
Sent to the evaluation server when a confirmed scam ends.
"""
from typing import List
from pydantic import BaseModel, Field

# Strict extractedIntelligence keys required by the participants PDF.
CALLBACK_INTEL_FIELDS = (
    "phoneNumbers",
    "bankAccounts",
    "upiIds",
    "phishingLinks",
    "emailAddresses",
)

# Internal-only intelligence keys that must be moved into agentNotes.
NON_CALLBACK_INTEL_FIELDS = (
    "suspiciousKeywords",
    "scammerNames",
    "staffIds",
    "ifscCodes",
    "panNumbers",
    "sebiHandles",
)


class ExtractedIntelligence(BaseModel):
    """Intelligence extracted from the scammer during conversation."""
    bankAccounts: List[str] = Field(default_factory=list, description="Bank account numbers")
    upiIds: List[str] = Field(default_factory=list, description="UPI IDs (e.g., name@upi)")
    phishingLinks: List[str] = Field(default_factory=list, description="Suspicious URLs")
    phoneNumbers: List[str] = Field(default_factory=list, description="Phone numbers")
    emailAddresses: List[str] = Field(default_factory=list, description="Email addresses")
    suspiciousKeywords: List[str] = Field(default_factory=list, description="Detected keywords")
    scammerNames: List[str] = Field(default_factory=list, description="Extracted scammer names")
    staffIds: List[str] = Field(default_factory=list, description="Extracted staff/employee IDs")
    ifscCodes: List[str] = Field(default_factory=list, description="Bank IFSC codes")
    panNumbers: List[str] = Field(default_factory=list, description="Indian PAN numbers")
    sebiHandles: List[str] = Field(default_factory=list, description="SEBI @valid handles")


class CallbackExtractedIntelligence(BaseModel):
    """Schema-locked extractedIntelligence for final callback JSON."""
    phoneNumbers: List[str] = Field(default_factory=list, description="Phone numbers")
    bankAccounts: List[str] = Field(default_factory=list, description="Bank account numbers")
    upiIds: List[str] = Field(default_factory=list, description="UPI IDs (e.g., name@upi)")
    phishingLinks: List[str] = Field(default_factory=list, description="Suspicious URLs")
    emailAddresses: List[str] = Field(default_factory=list, description="Email addresses")


class CallbackPayload(BaseModel):
    """
    Final callback payload sent to the evaluation endpoint.
    Triggered only when is_scam_confirmed=True AND conversation ends.
    
    Endpoint: POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult
    """
    sessionId: str = Field(..., description="Session identifier")
    scamDetected: bool = Field(..., description="Whether scam was confirmed")
    totalMessagesExchanged: int = Field(..., description="Total message count")
    engagementDurationSeconds: int = Field(default=0, description="Redundant duration")
    extractedIntelligence: CallbackExtractedIntelligence = Field(
        default_factory=CallbackExtractedIntelligence,
        description="Extracted scammer information"
    )
    agentNotes: str = Field(default="", description="Agent observations about the scam")
