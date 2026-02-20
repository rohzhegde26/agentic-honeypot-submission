"""
Pydantic models for webhook request and response.
Matches the API contract from 01_Problem_Statement.md
"""
from datetime import datetime
from typing import List, Literal, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class MessageInput(BaseModel):
    """Individual message in a conversation."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sender: str = Field(
        ..., 
        validation_alias=AliasChoices("sender"),
        description="Who sent the message"
    )
    text: str = Field(
        ..., 
        validation_alias=AliasChoices("text"),
        description="The message content"
    )
    timestamp: datetime = Field(
        ..., 
        validation_alias=AliasChoices("timestamp", "time"),
        description="When the message was sent"
    )


class MetadataInput(BaseModel):
    """Request metadata for context."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    channel: str = Field(default="SMS", description="Communication channel")
    language: str = Field(default="en", description="Language code")
    locale: str = Field(default="IN", description="Locale/region code")


class WebhookRequest(BaseModel):
    """
    Incoming webhook payload from the external system.
    Restored with aliases for backward compatibility.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sessionId: str = Field(
        ..., 
        validation_alias=AliasChoices("sessionId", "session_id", "id"),
        description="Unique session identifier"
    )
    message: MessageInput = Field(
        ..., 
        validation_alias=AliasChoices("message", "msg"),
        description="The current incoming message"
    )
    conversationHistory: Optional[List[MessageInput]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("conversationHistory", "history"),
        description="Previous messages"
    )
    metadata: Optional[MetadataInput] = Field(
        default_factory=MetadataInput,
        validation_alias=AliasChoices("metadata", "meta"),
        description="Metadata"
    )


class WebhookResponse(BaseModel):
    """
    Synchronous response sent back to the caller.
    Contains the agent's reply to the scammer.
    Updated to match the India AI Evaluation System scoring rubric (20 points for structure).
    """
    status: str = Field(..., description="Response status (success/error)")
    reply: str = Field(..., description="The agent's reply message")
    
    # Scoring Fields (20 points for structure)
    scamDetected: bool = Field(default=False, description="Whether scam was detected")
    scamType: str = Field(default="unknown", description="Categorized scam type")
    confidenceLevel: float = Field(default=0.0, description="Scam confidence score")
    sessionId: str = Field(default="", description="Redundant session identifier")

    totalMessagesExchanged: int = Field(default=0, description="Redundant message count")
    engagementDurationSeconds: int = Field(default=0, description="Redundant duration")
    
    extractedIntelligence: Optional[dict] = Field(
        default_factory=dict, 
        description="Scammer intel extracted so far"
    )
    engagementMetrics: Optional[dict] = Field(
        default_factory=dict, 
        description="totalMessagesExchanged, engagementDurationSeconds"
    )
    agentNotes: str = Field(default="", description="Agent observations")
