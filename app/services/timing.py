"""
Session Timing Service.
Instruments LangGraph node execution with precise wall-clock timestamps.
Used for identifying bottlenecks and optimizing response latency.
"""
import time
import logging
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

# In-memory store for recent session timings (last 50)
_recent_timings: deque = deque(maxlen=50)


class SessionTimer:
    """
    Tracks per-node wall-clock timing for a single agent session.
    
    Usage:
        timer = SessionTimer(session_id)
        timer.start("detector")
        # ... do work ...
        timer.stop("detector")
        summary = timer.summary()
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_start = time.perf_counter()
        self._entries: List[Dict] = []
        self._active: Dict[str, float] = {}  # node_name -> start_time
    
    def start(self, node_name: str, metadata: Optional[Dict] = None):
        """Mark the start of a node's execution."""
        self._active[node_name] = time.perf_counter()
    
    def stop(self, node_name: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Mark the end of a node's execution.
        Returns the timing entry dict for inclusion in AgentState.timing_log.
        """
        end_time = time.perf_counter()
        start_time = self._active.pop(node_name, end_time)
        duration_ms = round((end_time - start_time) * 1000, 1)
        
        entry = {
            "node": node_name,
            "duration_ms": duration_ms,
            "start_offset_ms": round((start_time - self.session_start) * 1000, 1),
        }
        if metadata:
            entry["metadata"] = metadata
        
        self._entries.append(entry)
        return entry
    
    def summary(self) -> Dict:
        """
        Generate a timing summary for the entire session.
        Returns a dict with total time and per-node breakdown.
        """
        total_ms = round((time.perf_counter() - self.session_start) * 1000, 1)
        
        summary = {
            "session_id": self.session_id,
            "total_ms": total_ms,
            "nodes": self._entries,
        }
        
        # Build one-line log string
        node_parts = " ".join(
            f"{e['node'].upper()}={e['duration_ms']}ms" for e in self._entries
        )
        log_line = f"TIMING session={self.session_id} TOTAL={total_ms}ms {node_parts}"
        logger.info(log_line)
        
        return summary


def record_session_timing(summary: Dict):
    """Store a session timing summary in the recent timings buffer."""
    _recent_timings.append(summary)


def get_recent_timings(limit: int = 50) -> List[Dict]:
    """Retrieve the most recent session timing summaries."""
    items = list(_recent_timings)
    return items[-limit:]
