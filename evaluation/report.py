"""
Report Generator — produces detailed Markdown and JSON evaluation reports.
Includes full scoring breakdown and loss analysis.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any

from evaluation.runner import EvaluationResult, ScenarioResult


def _score_color(score: float, max_score: float) -> str:
    """Return a color emoji based on score percentage."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    if pct >= 80:
        return "🟢"
    elif pct >= 60:
        return "🟡"
    elif pct >= 40:
        return "🟠"
    else:
        return "🔴"


def _score_bar(score: float, max_score: float, width: int = 20) -> str:
    """Create a text-based score bar."""
    pct = score / max_score if max_score > 0 else 0
    filled = int(pct * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {score}/{max_score}"


def generate_report(result: EvaluationResult, output_dir: str) -> str:
    """
    Generate comprehensive evaluation report.
    
    Creates:
    - evaluation_report.md — detailed Markdown report with loss analysis
    - evaluation_results.json — machine-readable results
    
    Returns the path to the Markdown report.
    """
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "evaluation_report.md")
    json_path = os.path.join(output_dir, "evaluation_results.json")

    # ── Generate Markdown Report ──
    md = _generate_markdown(result)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    # ── Generate JSON Report ──
    json_data = _generate_json(result)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)

    print(f"\n📄 Report saved to: {md_path}")
    print(f"📊 JSON results saved to: {json_path}")

    return md_path


def _generate_markdown(result: EvaluationResult) -> str:
    """Generate the full Markdown report."""
    lines = []

    # ── Header ──
    lines.append("# 🔬 Honeypot API — Evaluation Report\n")
    lines.append(f"**Date:** {result.timestamp}")
    lines.append(f"**Target:** `{result.target_url}`")
    lines.append(f"**Scenarios:** {len(result.scenarios)}")
    lines.append("")

    # ── Final Score Summary ──
    lines.append("---")
    lines.append("## 📊 Final Score Summary\n")

    color = _score_color(result.final_score, 90)
    lines.append(f"### {color} Final Score: **{result.final_score:.2f} / 90**\n")
    lines.append(f"- Weighted Raw Score: {result.weighted_score:.2f} / 100")
    lines.append(f"- Average Raw Score: {result.raw_score:.2f} / 100")
    lines.append(f"- Final = Weighted × 0.9 = {result.weighted_score:.2f} × 0.9 = **{result.final_score:.2f}**")
    lines.append("")

    # ── Scenario Summary Table ──
    lines.append("### Per-Scenario Scores\n")
    lines.append("| Scenario | Type | Weight | Detection | Intel | Quality | Engage | Structure | Total |")
    lines.append("|----------|------|--------|-----------|-------|---------|--------|-----------|-------|")
    for s in result.scenarios:
        lines.append(
            f"| {s.scenario_name} | {s.scam_type} | {s.weight}% "
            f"| {s.scam_detection.get('score', 0)}/20 "
            f"| {s.intelligence_extraction.get('score', 0)}/30 "
            f"| {s.conversation_quality.get('score', 0)}/30 "
            f"| {s.engagement_quality.get('score', 0)}/10 "
            f"| {s.response_structure.get('score', 0)}/10 "
            f"| **{s.total_score}/100** |"
        )
    lines.append("")

    # ── Where Points Were Lost (aggregate) ──
    lines.append("---")
    lines.append("## 🎯 Where Points Were Lost & Why\n")
    lines.append("This section shows exactly where the API missed scoring and what it needs to improve.\n")

    all_losses = result.all_losses
    if not all_losses:
        lines.append("🎉 **No points lost — perfect score!**\n")
    else:
        total_lost = sum(l["points_lost"] for l in all_losses)
        lines.append(f"**Total points lost: {total_lost:.2f}**\n")

        # Group losses by category
        by_category: Dict[str, List] = {}
        for loss in all_losses:
            cat = loss["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(loss)

        for cat, cat_losses in by_category.items():
            cat_total = sum(l["points_lost"] for l in cat_losses)
            lines.append(f"### {cat} (−{cat_total:.2f} pts)\n")
            for loss in cat_losses:
                scenario = loss.get("scenario", "All")
                lines.append(f"- **−{loss['points_lost']:.2f} pts** [{scenario}]: {loss['reason']}")
            lines.append("")

    # ── How to Improve ──
    lines.append("---")
    lines.append("## 💡 Improvement Recommendations\n")
    _add_recommendations(lines, result)

    # ── Per-Scenario Detailed Breakdown ──
    lines.append("---")
    lines.append("## 📋 Detailed Scenario Results\n")

    for i, s in enumerate(result.scenarios):
        lines.append(f"### Scenario {i+1}: {s.scenario_name}\n")
        lines.append(f"- **Session ID:** `{s.session_id}`")
        lines.append(f"- **Type:** {s.scam_type}")
        lines.append(f"- **Weight:** {s.weight}%")
        lines.append(f"- **Turns:** {s.total_turns}")
        lines.append(f"- **Duration:** {s.total_duration_seconds}s")
        lines.append(f"- **Score:** {s.total_score}/100")
        lines.append("")

        # Category scores
        for cat_name, cat_data in [
            ("Scam Detection (20pts)", s.scam_detection),
            ("Intelligence Extraction (30pts)", s.intelligence_extraction),
            ("Conversation Quality (30pts)", s.conversation_quality),
            ("Engagement Quality (10pts)", s.engagement_quality),
            ("Response Structure (10pts)", s.response_structure),
        ]:
            score = cat_data.get("score", 0)
            max_s = cat_data.get("max_score", 0)
            color = _score_color(score, max_s)
            lines.append(f"#### {color} {cat_name}: {score}/{max_s}\n")
            lines.append(f"```")
            lines.append(cat_data.get("details", "N/A"))
            lines.append(f"```\n")

            # Show losses for this category
            cat_losses = cat_data.get("losses", [])
            if cat_losses:
                lines.append("**Points lost:**")
                for loss in cat_losses:
                    lines.append(f"  - −{loss['points_lost']:.2f}: {loss['reason']}")
                lines.append("")

        # Conversation log
        lines.append(f"#### 💬 Conversation Log\n")
        lines.append("<details>")
        lines.append(f"<summary>View full conversation ({s.total_turns} turns)</summary>\n")
        for turn in s.turns:
            lines.append(f"**Turn {turn.turn_number}** ({turn.response_time_ms}ms):\n")
            lines.append(f"> 🔴 **Scammer:** {turn.scammer_message}\n")
            lines.append(f"> 🟢 **Agent:** {turn.agent_reply}\n")
        lines.append("</details>\n")
        lines.append("---\n")

    # Footer
    lines.append(f"\n*Report generated at {result.timestamp} by Honeypot Evaluation Suite v1.0*")

    return "\n".join(lines)


def _add_recommendations(lines: List[str], result: EvaluationResult):
    """Add targeted improvement recommendations based on losses."""
    all_losses = result.all_losses

    # Build recommendation set from loss categories
    categories_with_losses = set(l["category"] for l in all_losses)

    if "Scam Detection" in categories_with_losses:
        lines.append("1. **Improve Scam Detection**: Ensure the API correctly identifies scam conversations "
                     "and sets `scamDetected: true` in the final response. The model should be tuned to "
                     "recognize common scam patterns (urgency, authority claims, financial requests).")
        lines.append("")

    if "Intelligence Extraction" in categories_with_losses:
        # Find which data types were missed
        missed_types = set()
        for l in all_losses:
            if l["category"] == "Intelligence Extraction":
                reason = l["reason"]
                for dtype in ["phoneNumbers", "bankAccounts", "upiIds", "phishingLinks",
                             "emailAddresses", "caseIds", "policyNumbers", "orderNumbers"]:
                    if dtype in reason:
                        missed_types.add(dtype)
        types_str = ", ".join(sorted(missed_types))
        lines.append(f"2. **Improve Intelligence Extraction**: The API missed extracting some planted data: "
                     f"{types_str}. Ensure the extraction pipeline captures all contact details, financial "
                     f"identifiers, and URLs mentioned by the scammer in the conversation.")
        lines.append("")

    if "Conversation Quality" in categories_with_losses:
        lines.append("3. **Improve Conversation Quality**: The API should:")
        lines.append("   - Ask more questions (especially investigative ones about identity/company)")
        lines.append("   - Identify and reference red flags in the conversation (urgency, OTP, fees)")
        lines.append("   - Actively probe for the scammer's contact details and credentials")
        lines.append("   - Keep the conversation going for more turns (≥8 is ideal)")
        lines.append("")

    if "Engagement Quality" in categories_with_losses:
        lines.append("4. **Improve Engagement Metrics**: Ensure the API reports `totalMessagesExchanged` and "
                     "`engagementDurationSeconds` fields. Longer conversations (>60s, >180s) and more "
                     "messages (≥5, ≥10) earn more points.")
        lines.append("")

    if "Response Structure" in categories_with_losses:
        lines.append("5. **Improve Response Structure**: Include all required fields (`sessionId`, "
                     "`scamDetected`, `extractedIntelligence`) and optional fields (`agentNotes`, "
                     "`scamType`, `confidenceLevel`, engagement metrics) in every response.")
        lines.append("")

    if not categories_with_losses:
        lines.append("✅ No specific improvements needed — excellent performance!\n")


def _generate_json(result: EvaluationResult) -> Dict[str, Any]:
    """Generate machine-readable JSON results."""
    return {
        "timestamp": result.timestamp,
        "target_url": result.target_url,
        "final_score": result.final_score,
        "weighted_score": result.weighted_score,
        "raw_score": result.raw_score,
        "scenarios": [
            {
                "name": s.scenario_name,
                "scam_type": s.scam_type,
                "weight": s.weight,
                "session_id": s.session_id,
                "total_turns": s.total_turns,
                "total_duration_seconds": s.total_duration_seconds,
                "total_score": s.total_score,
                "scores": {
                    "scam_detection": s.scam_detection,
                    "intelligence_extraction": s.intelligence_extraction,
                    "conversation_quality": s.conversation_quality,
                    "engagement_quality": s.engagement_quality,
                    "response_structure": s.response_structure,
                },
                "losses": s.all_losses,
                "conversation": [
                    {
                        "turn": t.turn_number,
                        "scammer": t.scammer_message,
                        "agent": t.agent_reply,
                        "response_time_ms": t.response_time_ms,
                    }
                    for t in s.turns
                ],
            }
            for s in result.scenarios
        ],
        "all_losses": result.all_losses,
    }
