"""
Pydantic models for the final callback payload.
Sent to the evaluation server when a confirmed scam ends.
"""
from typing import List
from pydantic import BaseModel, Field


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


class CallbackPayload(BaseModel):
    """
    Final callback payload sent to the evaluation endpoint.
    Triggered only when is_scam_confirmed=True AND conversation ends.
    
    Endpoint: POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult
    """
    sessionId: str = Field(..., description="Session identifier")
    scamDetected: bool = Field(..., description="Whether scam was confirmed")
    totalMessagesExchanged: int = Field(..., description="Total message count")
    extractedIntelligence: ExtractedIntelligence = Field(
        default_factory=ExtractedIntelligence,
        description="Extracted scammer information"
    )
    agentNotes: str = Field(default="", description="Agent observations about the scam")
