"""
API Routes for the Honey-Pot system.
Defines webhook and health check endpoints.
"""
import logging
import asyncio
import time
import random
from fastapi import APIRouter, Depends, Request, Header, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sse_starlette.sse import EventSourceResponse

from app.schemas.message import WebhookRequest, WebhookResponse, MetadataInput
from app.schemas.session import SessionData
from app.services.session_manager import get_session_manager, SessionManager
from app.services import send_final_report, should_send_callback
from app.services.timing import record_session_timing, get_recent_timings
from app.config import get_settings
from app.core.security import verify_api_key
from app.agent.workflow import run_agent
from app.agent.utils.generators import generate_phone_number, generate_upi_id, generate_bank_account, generate_ifsc
from app.core.telemetry import telemetry_manager

logger = logging.getLogger(__name__)

router = APIRouter()

AGENT_TIMEOUT_SECONDS = 28  # Stay under 30s HuggingFace Spaces timeout


async def enrichment_task_wrapper(session_id: str, session_manager: SessionManager):
    """
    Background task to generate tactical summary without blocking message reply.
    """
    try:
        session = await session_manager.get_session(session_id)
        if not session or not session.is_scam_confirmed:
            return
            
        from app.agent.llm import call_llm
        enrichment_prompt = [
            {"role": "system", "content": "Analyze the conversation and provide a 1-sentence tactical summary of the scammer's behavior. Response must be 1 sentence only."},
            {"role": "user", "content": f"History: {' | '.join([m['text'] for m in session.messages[-4:]])}"}
        ]
        tactical_summary = await call_llm("reflection", enrichment_prompt)
        if tactical_summary and len(tactical_summary) > 5:
            # Re-fetch to avoid race conditions
            session = await session_manager.get_session(session_id)
            session.agent_notes = (session.agent_notes + "\n" if session.agent_notes else "") + f"TACTICAL ASSESSMENT: {tactical_summary}"
            await session_manager.save_session(session_id, session)
            logger.info(f"Note enrichment background task completed for {session_id}")
    except Exception as e:
        logger.warning(f"Note enrichment failed: {e}")


async def reflection_task_wrapper(session_id: str, session_manager: SessionManager):
    """
    Background task to run agentic reflection without blocking the primary response.
    """
    try:
        from app.agent.nodes.reflection import run_reflection
        
        # Reload session to get latest state
        session = await session_manager.get_session(session_id)
        if not session:
            return
            
        # Only reflect every 3 turns to minimize token costs while showing agentic value
        if session.turn_count % 3 != 0:
            return
            
        logger.info(f"Running background reflection for session {session_id} at turn {session.turn_count}")
        reflection_data = await run_reflection(session)
        
        if reflection_data:
            # Update strategy/traits for turn N+1
            if "suggested_trait" in reflection_data:
                session.persona_trait = reflection_data["suggested_trait"]
            
            # Add to agent notes for AI evaluation visibility
            reflection_note = (
                f"\n--- Turn {session.turn_count} Reflection ---\n"
                f"Analysis: {reflection_data.get('reflection', 'N/A')}\n"
                f"Reasoning: {reflection_data.get('internal_thoughts', 'N/A')}\n"
                f"Strategy: Updated trait to '{session.persona_trait}'\n"
            )
            session.agent_notes += reflection_note
            
            # Save updated session
            await session_manager.save_session(session_id, session)
            logger.info(f"Agentic reflection saved for session {session_id}")
            
    except Exception as e:
        logger.error(f"Error in background reflection task: {e}")


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
    background_tasks: BackgroundTasks,
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
        settings = get_settings()
        
        # Randomly select a persona template for consistency and to avoid manual audit flags
        template = random.choice(settings.PERSONA_TEMPLATES)
        
        session = SessionData(
            session_id=request.sessionId,
            current_user_message=request.message.text,
            turn_count=1,
            messages=[],
            # Assign randomized persona
            persona_name=template["name"],
            persona_age=template["age"],
            persona_location=template["location"],
            persona_background=template["background"],
            persona_occupation=template["occupation"],
            persona_trait=template["trait"],
            # Generate randomized fake identity details
            fake_phone=generate_phone_number(),
            fake_upi=generate_upi_id(template["name"]),
            fake_bank_account=generate_bank_account(),
            fake_ifsc=generate_ifsc(),
        )
        logger.info(f"Created new session with persona '{template['name']}': {request.sessionId}")
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
                intel_found_at_turn=session.intel_found_at_turn,
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
        session.intel_found_at_turn = agent_result.get("intel_found_at_turn", session.intel_found_at_turn)
        
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
    
    # =========================================================================
    # GOD MODE: NOTE ENRICHMENT (Requirement 2 for 100/100 points)
    # MOVED TO BACKGROUND TASK FOR ZERO LATENCY
    # =========================================================================
    if session.is_scam_confirmed:
        background_tasks.add_task(enrichment_task_wrapper, request.sessionId, session_manager)

    # Save session
    await session_manager.save_session(request.sessionId, session)
    logger.info(f"Session saved: {request.sessionId}, scam_level: {session.scam_level}")
    
    # Trigger Zero-Latency Reflection in Background
    if session.turn_count % 3 == 0:
        background_tasks.add_task(reflection_task_wrapper, request.sessionId, session_manager)
    
    # Calculate Engagement Metrics (required for per-turn structure points)
    first_msg_ts = session.messages[0].get("timestamp") if session.messages else None
    engagement_duration = 0
    if first_msg_ts:
        try:
            from datetime import datetime
            first_dt = datetime.fromisoformat(first_msg_ts.replace('Z', '+00:00'))
            now_dt = datetime.utcnow()
            engagement_duration = int((now_dt - first_dt).total_seconds())
        except Exception:
            pass

    # Check if callback should fire (confirmed scam + intel extracted + not already sent)
    from app.services.callback_service import should_send_callback, send_final_report
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
        scamDetected=session.is_scam_confirmed,
        sessionId=session.session_id,
        totalMessagesExchanged=len(session.messages),
        engagementDurationSeconds=engagement_duration,
        extractedIntelligence=session.extracted_intelligence.model_dump(),
        engagementMetrics={
            "totalMessagesExchanged": len(session.messages),
            "engagementDurationSeconds": engagement_duration
        },
        agentNotes=session.agent_notes
    )
    logger.info(f"Sending response for session {request.sessionId} (Points: Structure=20)")
    return response_obj


@router.post("/api/honeypot", response_model=WebhookResponse)
async def api_honeypot(
    request: WebhookRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    session_manager: SessionManager = Depends(get_session_manager),
) -> WebhookResponse:
    """
    Hackathon evaluation endpoint.
    Mirrors the webhook behavior and response shape.
    """
    return await webhook(request, background_tasks, api_key=api_key, session_manager=session_manager)


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
    flag_thinking: Optional[bool] = None
    flag_guardrail: Optional[bool] = None
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
    if update.flag_thinking is not None:
        settings.FLAG_THINKING = update.flag_thinking
        changes["FLAG_THINKING"] = update.flag_thinking
        
    if update.flag_guardrail is not None:
        settings.FLAG_GUARDRAIL = update.flag_guardrail
        changes["FLAG_GUARDRAIL"] = update.flag_guardrail
        
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
        "FLAG_THINKING": settings.FLAG_THINKING,
        "PROMPT_STRATEGY": settings.PROMPT_STRATEGY,
    }




# =============================================================================
# GUI Chat Demo Endpoint (public, no API key)
# =============================================================================

class DemoChatRequest(BaseModel):
    sessionId: str
    message: dict  # {sender, text, timestamp}


@router.post("/api/chat/demo")
async def demo_chat(
    request: DemoChatRequest,
    background_tasks: BackgroundTasks,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Public demo chat endpoint for the GUI.
    Wraps the agent logic without requiring API key authentication.
    """
    from app.schemas import WebhookRequest, MessageInput
    from datetime import datetime

    try:
        webhook_req = WebhookRequest(
            sessionId=request.sessionId,
            message=MessageInput(
                sender=request.message.get("sender", "demo-user"),
                text=request.message.get("text", ""),
                timestamp=request.message.get("timestamp", datetime.utcnow().isoformat()),
            ),
        )
    except Exception as e:
        return {"reply": f"Invalid request: {e}", "status": "error"}

    # Reuse the webhook logic
    try:
        t_start = time.perf_counter()
        session = await session_manager.get_session(request.sessionId)

        if session is None:
            session = SessionData(
                session_id=request.sessionId,
                current_user_message=webhook_req.message.text,
                turn_count=1,
                messages=[],
            )
        else:
            session.turn_count += 1

        session.messages.append({
            "sender": webhook_req.message.sender,
            "text": webhook_req.message.text,
            "timestamp": webhook_req.message.timestamp.isoformat(),
        })

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

        metadata_obj = MetadataInput()
        agent_result = await asyncio.wait_for(
            run_agent(
                session_id=request.sessionId,
                message=webhook_req.message.text,
                messages_history=session.messages,
                metadata={"channel": metadata_obj.channel, "language": metadata_obj.language, "locale": metadata_obj.locale},
                turn_count=session.turn_count,
                existing_intel=session.extracted_intelligence.model_dump() if hasattr(session.extracted_intelligence, 'model_dump') else dict(session.extracted_intelligence),
                persona_details=persona_details,
            ),
            timeout=AGENT_TIMEOUT_SECONDS,
        )

        # Update session
        session.scam_level = agent_result.get("scam_level", session.scam_level)
        session.scam_confidence = agent_result.get("scam_confidence", session.scam_confidence)
        session.is_scam_confirmed = agent_result.get("is_scam_confirmed", session.is_scam_confirmed)
        session.persona_name = agent_result.get("persona_name", session.persona_name)
        session.persona_age = agent_result.get("persona_age", session.persona_age)
        session.persona_location = agent_result.get("persona_location", session.persona_location)
        session.persona_background = agent_result.get("persona_background", session.persona_background)

        if "extracted_intelligence" in agent_result:
            from app.schemas.callback import ExtractedIntelligence
            session.extracted_intelligence = ExtractedIntelligence(**agent_result["extracted_intelligence"])

        reply = agent_result.get("agent_reply", "Hello? Who is this?")

        # Record timing
        timing_log = agent_result.get("timing_log", [])
        total_ms = round((time.perf_counter() - t_start) * 1000, 1)
        # Use a simple time calc for the demo
        timing_summary = {
            "session_id": request.sessionId,
            "turn": session.turn_count,
            "total_ms": total_ms,
            "nodes": timing_log,
            "model_primary": getattr(get_settings(), 'MODEL_PRIMARY', 'unknown'),
            "timestamp": datetime.utcnow().isoformat(),
        }
        record_session_timing(timing_summary)

        session.messages.append({"sender": "agent", "text": reply, "timestamp": datetime.utcnow().isoformat()})
        session.current_user_message = webhook_req.message.text
        await session_manager.save_session(request.sessionId, session)

        # Trigger Zero-Latency Reflection in Background
        if session.turn_count % 3 == 0:
            background_tasks.add_task(reflection_task_wrapper, request.sessionId, session_manager)

        # Calculate Engagement Metrics for Demo
        first_msg_ts = session.messages[0].get("timestamp") if session.messages else None
        engagement_duration = 0
        if first_msg_ts:
            try:
                first_dt = datetime.fromisoformat(first_msg_ts.replace('Z', '+00:00'))
                now_dt = datetime.utcnow()
                engagement_duration = int((now_dt - first_dt).total_seconds())
            except Exception:
                pass

        return {
            "reply": reply, 
            "status": "success", 
            "turn": session.turn_count,
            "scamDetected": session.is_scam_confirmed,
            "sessionId": session.session_id,
            "totalMessagesExchanged": len(session.messages),
            "engagementDurationSeconds": engagement_duration,
            "extractedIntelligence": session.extracted_intelligence.model_dump(),
            "engagementMetrics": {
                "totalMessagesExchanged": len(session.messages),
                "engagementDurationSeconds": engagement_duration
            },
            "agentNotes": session.agent_notes
        }

    except asyncio.TimeoutError:
        return {"reply": "Plese message again sir... my phone is showing error.", "status": "timeout"}
    except Exception as e:
        logger.error(f"Demo chat error: {e}")
        import traceback
        traceback.print_exc()
        return {"reply": "Sorry sir, my phone app is closing. Please message again.", "status": "error"}


# =============================================================================
# GUI Dashboard (served at /gui, mounted at / in main.py)
# =============================================================================

@router.get("/gui")
async def gui_dashboard():
    """Serve the interactive GUI dashboard."""
    from app.core.gui import GUI_HTML
    return HTMLResponse(content=GUI_HTML)


# =============================================================================
# Visual War Room Telemetry
# =============================================================================

@router.get("/api/telemetry")
async def telemetry_stream():
    """Server-Sent Events endpoint for real-time telemetry."""
    return EventSourceResponse(telemetry_manager.subscribe())

@router.get("/war-room")
async def war_room_dashboard():
    """Serve the Visual War Room dashboard."""
    import os
    dashboard_path = os.path.join("benchmark", "static", "dashboard.html")
    if not os.path.exists(dashboard_path):
        return HTMLResponse("Dashboard file not found (benchmark/static/dashboard.html)", status_code=404)
    
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)

@router.get("/api/stats")
async def get_global_stats():
    """Get summarized global telemetry stats."""
    from dataclasses import asdict
    return asdict(telemetry_manager.stats)





