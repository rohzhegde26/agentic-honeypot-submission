import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class GlobalStats:
    total_sessions: int = 0
    active_sessions: int = 0
    total_messages: int = 0
    total_upi_caught: int = 0
    total_banks_caught: int = 0
    total_links_caught: int = 0
    total_phones_caught: int = 0
    avg_scam_confidence: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

class TelemetryManager:
    _instance: Optional['TelemetryManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryManager, cls).__new__(cls)
            cls._instance.stats = GlobalStats()
            cls._instance.event_queues: List[asyncio.Queue] = []
            cls._instance.session_states: Dict[str, Dict[str, Any]] = {}
        return cls._instance

    def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update telemetry with new data from a session turn."""
        prev_state = self.session_states.get(session_id, {})
        
        # Update session state tracking
        self.session_states[session_id] = data
        
        # Update global aggregates if it's a new session
        if not prev_state:
            self.stats.total_sessions += 1
            self.stats.active_sessions += 1
            logger.info(f"Telemetry: New session {session_id} registered.")
        
        # Calculate deltas for intel yield
        intel = data.get("extracted_intelligence", {})
        prev_intel = prev_state.get("extracted_intelligence", {})
        
        self.stats.total_upi_caught += max(0, len(intel.get("upiIds", [])) - len(prev_intel.get("upiIds", [])))
        self.stats.total_banks_caught += max(0, len(intel.get("bankAccounts", [])) - len(prev_intel.get("bankAccounts", [])))
        self.stats.total_links_caught += max(0, len(intel.get("phishingLinks", [])) - len(prev_intel.get("phishingLinks", [])))
        self.stats.total_phones_caught += max(0, len(intel.get("phoneNumbers", [])) - len(prev_intel.get("phoneNumbers", [])))
        
        # Update other stats
        self.stats.total_messages += 1
        conf = data.get("scam_confidence", 0.0)
        # Moving average for confidence
        self.stats.avg_scam_confidence = (self.stats.avg_scam_confidence * 0.9) + (conf * 0.1)
        self.stats.last_updated = datetime.now().isoformat()

        # Create event for real-time stream
        event = {
            "type": "turn_update",
            "session_id": session_id,
            "scam_level": data.get("scam_level"),
            "scam_confidence": conf,
            "agent_reply": data.get("agent_reply", "")[:100],
            "intel_summary": f"UPI: {len(intel.get('upiIds', []))}, Bank: {len(intel.get('bankAccounts', []))}",
            "global_stats": asdict(self.stats)
        }
        
        asyncio.create_task(self._broadcast(event))

    def mark_session_complete(self, session_id: str, reason: str):
        """Mark a session as terminated."""
        if session_id in self.session_states:
            self.stats.active_sessions = max(0, self.stats.active_sessions - 1)
            event = {
                "type": "session_terminated",
                "session_id": session_id,
                "reason": reason,
                "global_stats": asdict(self.stats)
            }
            asyncio.create_task(self._broadcast(event))
            # Keep state for a while then cleanup if needed

    async def _broadcast(self, event: Dict[str, Any]):
        """Send event to all connected SSE clients."""
        if not self.event_queues:
            return
            
        data = f"data: {json.dumps(event)}\n\n"
        for queue in self.event_queues:
            await queue.put(data)

    async def subscribe(self):
        """Subscribe to the telemetry event stream."""
        queue = asyncio.Queue()
        self.event_queues.append(queue)
        try:
            # Send initial state
            yield f"data: {json.dumps({'type': 'init', 'global_stats': asdict(self.stats)})}\n\n"
            
            while True:
                data = await queue.get()
                yield data
        finally:
            self.event_queues.remove(queue)

# Global instances
telemetry_manager = TelemetryManager()
