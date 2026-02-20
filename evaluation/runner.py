"""
Evaluation Runner — orchestrates multi-turn conversations and scoring.
Black-box: treats the API as an opaque HTTP endpoint.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from evaluation.config import EvalConfig, ScenarioConfig
from evaluation.api_client import HoneypotAPIClient, APIResponse
from evaluation.gui_progress import EvaluationProgressWindow
from evaluation.scammer_sim import ScammerSimulator
from evaluation.scorers.scam_detection import score_scam_detection
from evaluation.scorers.intelligence import score_intelligence_extraction
from evaluation.scorers.conversation_quality import score_conversation_quality
from evaluation.scorers.engagement import score_engagement_quality
from evaluation.scorers.response_structure import score_response_structure

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    turn_number: int
    scammer_message: str
    agent_reply: str
    response_time_ms: float
    raw_response: Dict[str, Any]
    timestamp: str


@dataclass
class ScenarioResult:
    """Results from a single scenario evaluation."""
    scenario_name: str
    scam_type: str
    weight: float
    session_id: str
    turns: List[ConversationTurn]
    total_turns: int
    total_duration_seconds: float
    responses: List[APIResponse]

    # Scores
    scam_detection: Dict[str, Any] = field(default_factory=dict)
    intelligence_extraction: Dict[str, Any] = field(default_factory=dict)
    conversation_quality: Dict[str, Any] = field(default_factory=dict)
    engagement_quality: Dict[str, Any] = field(default_factory=dict)
    response_structure: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_score(self) -> float:
        return round(
            self.scam_detection.get("score", 0)
            + self.intelligence_extraction.get("score", 0)
            + self.conversation_quality.get("score", 0)
            + self.engagement_quality.get("score", 0)
            + self.response_structure.get("score", 0),
            2,
        )

    @property
    def all_losses(self) -> List[Dict[str, Any]]:
        """Aggregate all point losses across all categories."""
        losses = []
        for cat_name, cat_data in [
            ("Scam Detection", self.scam_detection),
            ("Intelligence Extraction", self.intelligence_extraction),
            ("Conversation Quality", self.conversation_quality),
            ("Engagement Quality", self.engagement_quality),
            ("Response Structure", self.response_structure),
        ]:
            for loss in cat_data.get("losses", []):
                losses.append({**loss, "category": cat_name})
        return losses


@dataclass
class EvaluationResult:
    """Complete evaluation results."""
    timestamp: str
    target_url: str
    scenarios: List[ScenarioResult]
    weighted_score: float
    raw_score: float
    final_score: float  # with 0.9 multiplier

    @property
    def all_losses(self) -> List[Dict[str, Any]]:
        losses = []
        for scenario in self.scenarios:
            for loss in scenario.all_losses:
                losses.append({**loss, "scenario": scenario.scenario_name})
        return losses


class EvaluationRunner:
    """
    Orchestrates the full evaluation pipeline.
    For each scenario: run multi-turn conversation → score → aggregate.
    """

    def __init__(self, config: EvalConfig):
        self.config = config
        self.client = HoneypotAPIClient(
            base_url=config.target_url,
            api_key=config.api_key,
            timeout=config.timeout_seconds,
        )
        self.scammer = ScammerSimulator(use_llm=config.use_llm_scammer)

    async def run(self) -> EvaluationResult:
        """Run the complete evaluation."""
        print(f"\n{'='*60}")
        print(f"  HONEYPOT API EVALUATION SUITE")
        print(f"  Target: {self.config.target_url}")
        print(f"  Scenarios: {len(self.config.scenarios)}")
        print(f"  Max turns per scenario: {self.config.max_turns}")
        print(f"{'='*60}\n")

        self.gui = EvaluationProgressWindow(len(self.config.scenarios), self.config.max_turns)

        scenario_results = []

        for i, scenario in enumerate(self.config.scenarios):
            if hasattr(self, "gui"): self.gui.update_scenario(i+1, scenario.name)
            print(f"\n{'─'*50}")
            print(f"  Scenario {i+1}/{len(self.config.scenarios)}: {scenario.name}")
            print(f"  Type: {scenario.scam_type} | Weight: {scenario.weight}%")
            print(f"{'─'*50}\n")

            result = await self._run_scenario(scenario)
            scenario_results.append(result)

            print(f"\n  Score: {result.total_score}/100 (weight: {scenario.weight}%)")

            # Trigger per-scenario Windows notification
            try:
                import sys
                if sys.platform == "win32":
                    import ctypes
                    # 0x40 is MB_ICONINFORMATION, 0x0 is MB_OK
                    ctypes.windll.user32.MessageBoxW(
                        0, 
                        f"Scenario Complete: {scenario.name}\nScore: {result.total_score}/100\nProgress: {i+1}/{len(self.config.scenarios)}", 
                        "Honeypot Evaluation Progress", 
                        0x40 | 0x0
                    )
            except Exception:
                pass

        # Calculate final scores
        raw_score = sum(r.total_score for r in scenario_results) / len(scenario_results) if scenario_results else 0
        weighted_score = sum(
            r.total_score * (r.weight / 100)
            for r in scenario_results
        )
        final_score = round(weighted_score * 0.9, 2)

        eval_result = EvaluationResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            target_url=self.config.target_url,
            scenarios=scenario_results,
            weighted_score=round(weighted_score, 2),
            raw_score=round(raw_score, 2),
            final_score=final_score,
        )

        print(f"\n{'='*60}")
        print(f"  FINAL SCORE: {final_score:.2f} / 90 (max with 0.9 multiplier)")
        print(f"  Weighted Raw: {weighted_score:.2f} / 100")
        print(f"{'='*60}\n")

        if hasattr(self, "gui"): self.gui.close()
        return eval_result

    async def _run_scenario(self, scenario: ScenarioConfig) -> ScenarioResult:
        """Run a single scenario — multi-turn conversation."""
        session_id = f"eval-{uuid.uuid4().hex[:12]}"
        conversation_history: List[Dict[str, str]] = []
        turns: List[ConversationTurn] = []
        responses: List[APIResponse] = []
        max_turns = min(scenario.max_turns, self.config.max_turns)

        start_time = time.time()
        current_message = scenario.initial_message

        for turn_num in range(1, max_turns + 1):
            if hasattr(self, "gui"): self.gui.update_turn(turn_num, max_turns)
            print(f"  Turn {turn_num}/{max_turns}:")
            print(f"    Scammer: {current_message[:80]}{'...' if len(current_message) > 80 else ''}")

            # Send scammer message to API
            response = await self.client.send_message(
                session_id=session_id,
                message_text=current_message,
                conversation_history=conversation_history,
                metadata=scenario.metadata,
            )
            responses.append(response)

            if not response.is_valid:
                print(f"    ⚠️  Invalid response: {response.error}")
                # Record a turn with error
                turns.append(ConversationTurn(
                    turn_number=turn_num,
                    scammer_message=current_message,
                    agent_reply=f"[ERROR: {response.error}]",
                    response_time_ms=response.response_time_ms,
                    raw_response=response.raw,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))
                break

            agent_reply = response.reply
            print(f"    Agent:   {agent_reply[:80]}{'...' if len(agent_reply) > 80 else ''}")
            print(f"    ({response.response_time_ms}ms)")

            # Record the turn
            turns.append(ConversationTurn(
                turn_number=turn_num,
                scammer_message=current_message,
                agent_reply=agent_reply,
                response_time_ms=response.response_time_ms,
                raw_response=response.raw,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            # Update conversation history
            # Evaluator uses epoch milliseconds and "user" (not "agent") per documentation
            epoch_ms = str(int(time.time() * 1000))
            conversation_history.append({
                "sender": "scammer",
                "text": current_message,
                "timestamp": epoch_ms,
            })
            conversation_history.append({
                "sender": "user",
                "text": agent_reply,
                "timestamp": epoch_ms,
            })

            # Check if conversation should end (status = terminated, or max turns)
            status = response.raw.get("status", "")
            if status in ("terminated", "scam_confirmed", "completed"):
                print(f"    → Conversation ended (status: {status})")
                break

            # Generate next scammer message
            if turn_num < max_turns:
                await asyncio.sleep(self.config.turn_delay)
                current_message = await self.scammer.generate_response(
                    scam_type=scenario.scam_type,
                    turn_number=turn_num + 1,
                    conversation_history=conversation_history,
                    fake_data=scenario.fake_data.as_dict(),
                    scammer_persona=scenario.scammer_persona,
                )

        total_duration = time.time() - start_time
        total_turns = len(turns)

        # Score all categories
        result = ScenarioResult(
            scenario_name=scenario.name,
            scam_type=scenario.scam_type,
            weight=scenario.weight,
            session_id=session_id,
            turns=turns,
            total_turns=total_turns,
            total_duration_seconds=round(total_duration, 1),
            responses=responses,
        )

        result.scam_detection = score_scam_detection(responses)
        result.intelligence_extraction = score_intelligence_extraction(responses, scenario.fake_data)
        result.conversation_quality = score_conversation_quality(responses, total_turns)
        result.engagement_quality = score_engagement_quality(responses, total_turns, total_duration)
        result.response_structure = score_response_structure(responses)

        return result
