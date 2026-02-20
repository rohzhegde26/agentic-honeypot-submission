"""
CLI entry point for the Honeypot API Evaluation Suite.
Usage: python -m evaluation [options]
"""
import argparse
import asyncio
import logging
import os
import sys

# Add parent directory to path so we can import evaluation package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from evaluation.config import EvalConfig, load_scenarios
from evaluation.runner import EvaluationRunner
from evaluation.report import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="🔬 Honeypot API Evaluation Suite — Black-box testing against the official scoring rubric.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m evaluation
  python -m evaluation --url http://localhost:8000/webhook --api-key mykey
  python -m evaluation --url https://my-app.hf.space/webhook --turns 8
  python -m evaluation --no-llm --turns 5
  python -m evaluation --scenarios evaluation/scenarios/bank_fraud.json
        """,
    )
    parser.add_argument(
        "--url",
        default=os.getenv("EVAL_TARGET_URL", "http://localhost:8000/webhook"),
        help="Target API URL (default: http://localhost:8000/webhook)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_SECRET_KEY", os.getenv("API_KEY", "")),
        help="API key for authentication (default: from .env)",
    )
    parser.add_argument(
        "--scenarios",
        default=os.path.join(os.path.dirname(__file__), "scenarios"),
        help="Path to scenario JSON file or directory (default: evaluation/scenarios/)",
    )
    parser.add_argument(
        "--output",
        default="evaluation_report",
        help="Output directory for reports (default: evaluation_report/)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Maximum turns per scenario (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between turns in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM-powered scammer simulator (use templates instead)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--accelerated",
        action="store_true",
        help="Enable accelerated time simulation",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of scenarios to run concurrently (default: 5)",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Load scenarios
    try:
        scenarios = load_scenarios(args.scenarios)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if not scenarios:
        print("❌ No scenarios found. Provide scenario JSON files in the scenarios directory.")
        sys.exit(1)

    print(f"📋 Loaded {len(scenarios)} scenario(s): {', '.join(s.name for s in scenarios)}")

    # Build configuration
    config = EvalConfig(
        target_url=args.url,
        api_key=args.api_key,
        max_turns=args.turns,
        timeout_seconds=args.timeout,
        output_dir=args.output,
        scenarios=scenarios,
        use_llm_scammer=not args.no_llm,
        turn_delay=args.delay,
        accelerated=args.accelerated,
        concurrency=args.concurrency,
    )

    # Run evaluation
    runner = EvaluationRunner(config)

    try:
        result = asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # Generate reports
    report_path = generate_report(result, args.output)

    # Print summary to console
    print(f"\n{'='*60}")
    print(f"  EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Final Score:  {result.final_score:.2f} / 90")
    print(f"  Weighted:     {result.weighted_score:.2f} / 100")
    print()

    # Print top losses
    losses = result.all_losses
    if losses:
        # Sort by points lost (descending)
        losses.sort(key=lambda x: x["points_lost"], reverse=True)
        print(f"  TOP SCORING GAPS:")
        for i, loss in enumerate(losses[:5]):
            print(f"    {i+1}. −{loss['points_lost']:.1f}pts [{loss['category']}]: {loss['reason'][:80]}...")
        if len(losses) > 5:
            remaining = sum(l["points_lost"] for l in losses[5:])
            print(f"    ... and {len(losses)-5} more (−{remaining:.1f}pts total)")
    else:
        print("  🎉 Perfect score — no points lost!")

    print(f"\n  Full report: {report_path}")
    print(f"{'='*60}\n")
    
    # Trigger a Windows notification to alert the user that the tests are complete
    try:
        if sys.platform == "win32":
            import ctypes
            # 0x40 is MB_ICONINFORMATION, 0x0 is MB_OK
            ctypes.windll.user32.MessageBoxW(0, f"The evaluation suite has finished running!\n\nFinal Score: {result.weighted_score:.2f} / 100", "Evaluation Complete", 0x40 | 0x0)
    except Exception:
        pass


if __name__ == "__main__":
    main()
