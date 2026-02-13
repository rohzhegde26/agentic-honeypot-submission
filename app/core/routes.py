"""
API Routes for the Honey-Pot system.
Defines webhook and health check endpoints.
"""
import logging
import asyncio
import time
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from app.schemas import WebhookRequest, WebhookResponse, SessionData, MetadataInput
from app.services import get_session_manager, SessionManager
from app.services import send_final_report, should_send_callback
from app.services.timing import record_session_timing, get_recent_timings
from app.config import get_settings
from app.core.security import verify_api_key
from app.agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter()

AGENT_TIMEOUT_SECONDS = 28  # Stay under 30s HuggingFace Spaces timeout


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Does not touch Redis or agent logic.
    """
    return {
        "status": "ok",
    }


@router.get("/health/diag")
async def health_diag():
    """
    Public diagnostic endpoint to verify environment loading.
    Does NOT reveal actual keys, only if they are set.
    """
    from app.config import get_settings
    settings = get_settings()
    return {
        "UPSTASH_REDIS_SET": bool(settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN),
        "API_SECRET_KEY_SET": bool(settings.API_SECRET_KEY),
        "NVIDIA_PRIMARY_SET": bool(settings.NVIDIA_API_KEY_PRIMARY),
        "NVIDIA_FALLBACK_SET": bool(settings.NVIDIA_API_KEY_FALLBACK),
        "DEBUG_MODE": settings.DEBUG,
        "MODEL_PRIMARY": settings.MODEL_PRIMARY,
        "MODEL_FALLBACK": settings.MODEL_FALLBACK,
    }


@router.api_route(
    "/honeypot/test",
    methods=["GET", "POST"],
    dependencies=[Depends(verify_api_key)],
)
async def honeypot_test():
    """
    Infrastructure test endpoint for hackathon reachability checks.
    Accepts GET/POST, ignores request body, and does not invoke the agent.
    """
    return {
        "status": "ok",
        "service": "agentic-honeypot",
        "message": "endpoint reachable",
    }


@router.post("/webhook", response_model=WebhookResponse)
async def webhook(
    request: WebhookRequest,
    api_key: str = Depends(verify_api_key),
    session_manager: SessionManager = Depends(get_session_manager),
) -> WebhookResponse:
    """
    Main webhook endpoint for incoming scam messages.
    
    This endpoint:
    1. Validates the incoming request
    2. Retrieves or creates a session
    3. Runs the LangGraph agent (Detect -> Engage)
    4. Saves the updated session
    5. Returns the agent's reply
    """
    logger.info(f"Webhook received for session: {request.sessionId}")
    t_webhook_start = time.perf_counter()
    
    # Get or create session
    session = await session_manager.get_session(request.sessionId)
    
    if session is None:
        # Create new session if none exists
        session = SessionData(
            session_id=request.sessionId,
            current_user_message=request.message.text,
            turn_count=1,
            messages=[],
        )
        logger.info(f"Created new session: {request.sessionId}")
    else:
        # Update existing session
        session.turn_count += 1
        logger.info(f"Resuming session: {request.sessionId}, turn: {session.turn_count}")
    
    # Add incoming message to history
    session.messages.append({
        "sender": request.message.sender,
        "text": request.message.text,
        "timestamp": request.message.timestamp.isoformat(),
    })
    
    # Run LangGraph agent
    try:
        # Prepare persona details from session
        persona_details = {
            "persona_name": session.persona_name,
            "persona_age": session.persona_age,
            "persona_location": session.persona_location,
            "persona_background": session.persona_background,
            "persona_occupation": session.persona_occupation,
            "persona_trait": session.persona_trait,
            "fake_phone": session.fake_phone,
            "fake_upi": session.fake_upi,
            "fake_bank_account": session.fake_bank_account,
            "fake_ifsc": session.fake_ifsc,
        }
        
        metadata_obj = request.metadata or MetadataInput()
        agent_result = await asyncio.wait_for(
            run_agent(
                session_id=request.sessionId,
                message=request.message.text,
                messages_history=session.messages,
                metadata={
                    "channel": metadata_obj.channel,
                    "language": metadata_obj.language,
                    "locale": metadata_obj.locale,
                },
                turn_count=session.turn_count,
                existing_intel=session.extracted_intelligence.model_dump() if hasattr(session.extracted_intelligence, 'model_dump') else dict(session.extracted_intelligence),
                persona_details=persona_details,
            ),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        
        # Update session from agent result
        session.scam_level = agent_result.get("scam_level", session.scam_level)
        session.scam_confidence = agent_result.get("scam_confidence", session.scam_confidence)
        session.is_scam_confirmed = agent_result.get("is_scam_confirmed", session.is_scam_confirmed)
        session.agent_notes = agent_result.get("agent_notes", session.agent_notes)
        
        # Update persona details (in case they were initialized in this turn)
        session.persona_name = agent_result.get("persona_name", session.persona_name)
        session.persona_age = agent_result.get("persona_age", session.persona_age)
        session.persona_location = agent_result.get("persona_location", session.persona_location)
        session.persona_background = agent_result.get("persona_background", session.persona_background)
        session.persona_occupation = agent_result.get("persona_occupation", session.persona_occupation)
        session.persona_trait = agent_result.get("persona_trait", session.persona_trait)
        session.fake_phone = agent_result.get("fake_phone", session.fake_phone)
        session.fake_upi = agent_result.get("fake_upi", session.fake_upi)
        session.fake_bank_account = agent_result.get("fake_bank_account", session.fake_bank_account)
        session.fake_ifsc = agent_result.get("fake_ifsc", session.fake_ifsc)
        
        # Update extracted intelligence
        if "extracted_intelligence" in agent_result:
            from app.schemas.callback import ExtractedIntelligence
            session.extracted_intelligence = ExtractedIntelligence(**agent_result["extracted_intelligence"])
        
        # Update termination reason and agent notes
        session.termination_reason = agent_result.get("termination_reason", session.termination_reason)
        session.agent_notes = agent_result.get("agent_notes", session.agent_notes)
        
        reply = agent_result.get("agent_reply", "Hello? Who is this?")
        
        # Record timing
        timing_log = agent_result.get("timing_log", [])
        total_ms = round((time.perf_counter() - t_webhook_start) * 1000, 1)
        timing_summary = {
            "session_id": request.sessionId,
            "turn": session.turn_count,
            "total_ms": total_ms,
            "nodes": timing_log,
            "model_primary": getattr(get_settings(), 'MODEL_PRIMARY', 'unknown'),
        }
        record_session_timing(timing_summary)
        node_parts = " ".join(f"{e.get('node','?').upper()}={e.get('duration_ms',0)}ms" for e in timing_log)
        logger.info(f"TIMING session={request.sessionId} turn={session.turn_count} TOTAL={total_ms}ms {node_parts}")
        
    except asyncio.TimeoutError:
        logger.error(f"Agent timeout for session {request.sessionId} after {AGENT_TIMEOUT_SECONDS}s")
        reply = "Plese message again sir... my phone is showing error and I am not able to see properly."
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Agent error: {e}")
        reply = "Sorry sir my phone app is closing again and again. Please message again."
    
    # Add agent reply to messages
    session.messages.append({
        "sender": "agent",
        "text": reply,
        "timestamp": request.message.timestamp.isoformat(),
    })
    session.current_user_message = request.message.text
    
    # Save session
    await session_manager.save_session(request.sessionId, session)
    logger.info(f"Session saved: {request.sessionId}, scam_level: {session.scam_level}")
    
    # Check if callback should fire (confirmed scam + intel extracted + not already sent)
    if should_send_callback(session):
        logger.info(f"Triggering callback for session {request.sessionId}")
        callback_success = await send_final_report(session)
        if callback_success:
            session.callback_sent = True
            await session_manager.save_session(request.sessionId, session)
            logger.info(f"Callback successful for session {request.sessionId}")
        else:
            logger.error(f"Callback failed for session {request.sessionId}")
    
    response_obj = WebhookResponse(
        status="success",
        reply=reply,
    )
    logger.info(f"Sending response for session {request.sessionId}: {response_obj.model_dump_json()}")
    return response_obj


@router.post("/api/honeypot", response_model=WebhookResponse)
async def api_honeypot(
    request: WebhookRequest,
    api_key: str = Depends(verify_api_key),
    session_manager: SessionManager = Depends(get_session_manager),
) -> WebhookResponse:
    """
    Hackathon evaluation endpoint.
    Mirrors the webhook behavior and response shape.
    """
    return await webhook(request, api_key=api_key, session_manager=session_manager)


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.get("/admin/timing")
async def admin_timing(limit: int = 20):
    """Returns recent session timing data for performance analysis."""
    return {"timings": get_recent_timings(limit)}


class ConfigUpdate(BaseModel):
    model_primary: Optional[str] = None
    model_fallback: Optional[str] = None
    debug: Optional[bool] = None
    flag_llm_extraction: Optional[bool] = None
    flag_stalling: Optional[bool] = None
    flag_verbose_logging: Optional[bool] = None
    prompt_strategy: Optional[str] = None  # "default", "aggressive", "defensive"


@router.post("/admin/config", dependencies=[Depends(verify_api_key)])
async def admin_config_update(update: ConfigUpdate):
    """Hot-swap model config at runtime without restarting."""
    from app.config import get_settings
    from app.agent.llm import clear_client_cache
    
    settings = get_settings()
    changes = {}
    
    if update.model_primary is not None:
        settings.MODEL_PRIMARY = update.model_primary
        changes["MODEL_PRIMARY"] = update.model_primary
    if update.model_fallback is not None:
        settings.MODEL_FALLBACK = update.model_fallback
        changes["MODEL_FALLBACK"] = update.model_fallback
    if update.debug is not None:
        settings.DEBUG = update.debug
        changes["DEBUG"] = update.debug
    if update.flag_llm_extraction is not None:
        settings.FLAG_LLM_EXTRACTION = update.flag_llm_extraction
        changes["FLAG_LLM_EXTRACTION"] = update.flag_llm_extraction
    if update.flag_stalling is not None:
        settings.FLAG_STALLING = update.flag_stalling
        changes["FLAG_STALLING"] = update.flag_stalling
    if update.flag_verbose_logging is not None:
        settings.FLAG_VERBOSE_LOGGING = update.flag_verbose_logging
        changes["FLAG_VERBOSE_LOGGING"] = update.flag_verbose_logging
    if update.prompt_strategy is not None:
        if update.prompt_strategy in ("default", "aggressive", "defensive"):
            settings.PROMPT_STRATEGY = update.prompt_strategy
            changes["PROMPT_STRATEGY"] = update.prompt_strategy
        else:
            return {"status": "error", "message": "Invalid strategy. Choose: default, aggressive, defensive"}
    
    # Clear client cache so new config takes effect
    clear_client_cache()
    
    logger.info(f"Config updated: {changes}")
    return {"status": "updated", "changes": changes}


@router.get("/admin/config")
async def admin_config_view():
    """View current runtime config."""
    from app.config import get_settings
    settings = get_settings()
    return {
        "MODEL_PRIMARY": settings.MODEL_PRIMARY,
        "MODEL_FALLBACK": settings.MODEL_FALLBACK,
        "DEBUG": settings.DEBUG,
        "FLAG_LLM_EXTRACTION": settings.FLAG_LLM_EXTRACTION,
        "FLAG_STALLING": settings.FLAG_STALLING,
        "FLAG_VERBOSE_LOGGING": settings.FLAG_VERBOSE_LOGGING,
        "PROMPT_STRATEGY": settings.PROMPT_STRATEGY,
    }


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Honeypot Performance Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',sans-serif; background:#0d1117; color:#c9d1d9; padding:24px; }
  h1 { color:#58a6ff; margin-bottom:8px; font-size:1.6rem; }
  .subtitle { color:#8b949e; margin-bottom:24px; font-size:0.9rem; }
  .stats { display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }
  .stat-card { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px 24px; min-width:140px; }
  .stat-value { font-size:1.8rem; font-weight:700; color:#58a6ff; }
  .stat-label { font-size:0.8rem; color:#8b949e; margin-top:4px; }
  .config-panel { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; margin-bottom:24px; }
  .config-panel h3 { color:#58a6ff; margin-bottom:8px; }
  .flag { display:inline-block; padding:4px 10px; border-radius:4px; font-size:0.8rem; margin:2px 4px; }
  .flag-on { background:#238636; color:#fff; }
  .flag-off { background:#da3633; color:#fff; }
  .flag-strategy { background:#1f6feb; color:#fff; }
  table { width:100%; border-collapse:collapse; background:#161b22; border-radius:8px; overflow:hidden; }
  th { background:#21262d; color:#8b949e; text-align:left; padding:10px 12px; font-size:0.85rem; font-weight:600; }
  td { padding:10px 12px; border-top:1px solid #30363d; font-size:0.85rem; }
  tr:hover { background:#1c2128; }
  .fast { color:#3fb950; }
  .medium { color:#d29922; }
  .slow { color:#f85149; }
  .refresh { color:#8b949e; font-size:0.75rem; margin-top:12px; }
</style>
</head>
<body>
  <h1>🍯 Honeypot Performance Dashboard</h1>
  <p class="subtitle">Auto-refreshes every 5 seconds</p>
  <div class="config-panel" id="config">Loading config...</div>
  <div class="stats" id="stats">Loading...</div>
  <table>
    <thead><tr><th>Session</th><th>Turn</th><th>Total</th><th>Detector</th><th>Extractor</th><th>Persona</th><th>Output</th><th>Model</th></tr></thead>
    <tbody id="tbody">Loading...</tbody>
  </table>
  <p class="refresh" id="lastUpdate"></p>
<script>
function colorize(ms) {
  if (ms === '-') return '';
  const v = parseFloat(ms);
  if (v < 1000) return 'fast';
  if (v < 5000) return 'medium';
  return 'slow';
}
function nodeMs(nodes, name) {
  const n = nodes.find(e => e.node === name);
  if (!n) return '-';
  let t = n.duration_ms + 'ms';
  if (n.llm_ms) t += ` (LLM: ${n.llm_ms}ms)`;
  return t;
}
async function refresh() {
  try {
    const [tRes, cRes] = await Promise.all([fetch('/admin/timing?limit=30'), fetch('/admin/config')]);
    const tData = await tRes.json();
    const cData = await cRes.json();
    // Config panel
    document.getElementById('config').innerHTML = `<h3>Runtime Config</h3>
      <span class="flag flag-strategy">${cData.PROMPT_STRATEGY} strategy</span>
      <span class="flag ${cData.FLAG_LLM_EXTRACTION?'flag-on':'flag-off'}">LLM Extraction: ${cData.FLAG_LLM_EXTRACTION?'ON':'OFF'}</span>
      <span class="flag ${cData.FLAG_STALLING?'flag-on':'flag-off'}">Stalling: ${cData.FLAG_STALLING?'ON':'OFF'}</span>
      <span class="flag ${cData.FLAG_VERBOSE_LOGGING?'flag-on':'flag-off'}">Verbose: ${cData.FLAG_VERBOSE_LOGGING?'ON':'OFF'}</span>
      <span class="flag flag-strategy">${cData.MODEL_PRIMARY.split('/').pop()}</span>`;
    // Stats
    const timings = tData.timings || [];
    if (timings.length === 0) {
      document.getElementById('stats').innerHTML = '<div class="stat-card"><div class="stat-label">No data yet</div></div>';
      document.getElementById('tbody').innerHTML = '<tr><td colspan="8">No timing data. Send a message to populate.</td></tr>';
    } else {
      const totals = timings.map(t => t.total_ms);
      const avg = (totals.reduce((a,b)=>a+b,0)/totals.length).toFixed(0);
      const sorted = [...totals].sort((a,b)=>a-b);
      const p50 = sorted[Math.floor(sorted.length*0.5)]?.toFixed(0) || '-';
      const p95 = sorted[Math.floor(sorted.length*0.95)]?.toFixed(0) || '-';
      const fastest = Math.min(...totals).toFixed(0);
      document.getElementById('stats').innerHTML = `
        <div class="stat-card"><div class="stat-value">${timings.length}</div><div class="stat-label">Sessions</div></div>
        <div class="stat-card"><div class="stat-value ${colorize(avg)}">${avg}ms</div><div class="stat-label">Avg Latency</div></div>
        <div class="stat-card"><div class="stat-value ${colorize(p50)}">${p50}ms</div><div class="stat-label">P50</div></div>
        <div class="stat-card"><div class="stat-value ${colorize(p95)}">${p95}ms</div><div class="stat-label">P95</div></div>
        <div class="stat-card"><div class="stat-value ${colorize(fastest)}">${fastest}ms</div><div class="stat-label">Fastest</div></div>`;
      document.getElementById('tbody').innerHTML = timings.reverse().map(t => {
        const nodes = t.nodes || [];
        return `<tr>
          <td>${t.session_id?.substring(0,12) || '?'}</td>
          <td>${t.turn || '-'}</td>
          <td class="${colorize(t.total_ms)}">${t.total_ms}ms</td>
          <td>${nodeMs(nodes,'detector')}</td>
          <td>${nodeMs(nodes,'extractor')}</td>
          <td>${nodeMs(nodes,'persona')}</td>
          <td>${nodeMs(nodes,'output')}</td>
          <td>${(t.model_primary||'').split('/').pop()}</td>
        </tr>`;
      }).join('');
    }
    document.getElementById('lastUpdate').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
  } catch(e) { console.error(e); }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@router.get("/admin/dashboard")
async def admin_dashboard():
    """Response time dashboard with live auto-refresh."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=DASHBOARD_HTML)

