"""Runner script for evaluating memory state quality.

This script loads a JSON state dump and a Markdown leaderboard file,
runs the evaluation, and generates a formatted report.

Usage:
    python run_eval.py --state state/state_dump_final.json --leaderboard src/evaluations/leaderboard/literary_basic.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from src.evaluations.engine import run_evaluation
from src.evaluations.loader import parse_leaderboard_markdown
from src.evaluations.models import CheckPriority, EvaluationResult


def format_console_report(result: EvaluationResult) -> str:
    """Format the evaluation result as a colorful console report.

    Args:
        result: The evaluation result to format

    Returns:
        Formatted string with emojis and status indicators
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("  📊 MEMORY STATE QUALITY EVALUATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Overall status
    status_emoji = "✅" if result.overall_status == "PASS" else "❌"
    lines.append(f"Overall Status: {status_emoji} {result.overall_status}")
    lines.append("")

    # Summary metrics
    lines.append("Summary:")
    lines.append(f"  • Total Checks: {result.total_checks}")
    lines.append(f"  • Passed: {result.passed_checks} ✅")
    lines.append(f"  • Failed: {result.failed_checks} ❌")
    lines.append(
        f"  • Score: {result.score_percentage:.1f}% ({result.passed_checks}/{result.total_checks})"
    )
    lines.append("")
    lines.append(
        f"  • Must-Have Checks: {result.must_have_passed}/{result.must_have_total}"
    )
    lines.append("")

    # Individual check results
    lines.append("-" * 80)
    lines.append("Individual Check Results:")
    lines.append("-" * 80)
    lines.append("")

    for check_result in result.check_results:
        status = "✅ PASS" if check_result.passed else "❌ FAIL"
        lines.append(f"{check_result.check_id}: {status}")
        lines.append(f"  Reasoning: {check_result.reasoning}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main() -> int:
    """Main entry point for the evaluation runner.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Evaluate memory state quality against leaderboard criteria"
    )
    parser.add_argument(
        "--state",
        type=str,
        required=True,
        help="Path to JSON state dump file",
    )
    parser.add_argument(
        "--leaderboard",
        type=str,
        required=True,
        help="Path to Markdown leaderboard file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional path to save JSON report",
    )

    args = parser.parse_args()

    # Load environment variables from a .env file if present
    # This allows API keys and other config to be set without exporting to the shell
    load_dotenv()

    # Validate input files
    state_path = Path(args.state)
    leaderboard_path = Path(args.leaderboard)

    if not state_path.exists():
        print(f"❌ Error: State file not found: {state_path}")
        return 1

    if not leaderboard_path.exists():
        print(f"❌ Error: Leaderboard file not found: {leaderboard_path}")
        return 1

    try:
        # Load the leaderboard
        print(f"📋 Loading leaderboard from: {leaderboard_path}")
        checks = parse_leaderboard_markdown(leaderboard_path)
        print(f"   Found {len(checks)} quality checks")

        # Count by priority
        must_have = sum(1 for c in checks if c.priority == CheckPriority.MUST_HAVE)
        should_have = sum(1 for c in checks if c.priority == CheckPriority.SHOULD_HAVE)
        nice_to_have = sum(
            1 for c in checks if c.priority == CheckPriority.NICE_TO_HAVE
        )

        print(
            f"   (🔴 {must_have} MUST-HAVE, 🟡 {should_have} SHOULD-HAVE, 🟢 {nice_to_have} NICE-TO-HAVE)"
        )
        print("")

        # Run evaluation
        print(f"🔍 Evaluating state: {state_path}")
        print("   This may take a moment...")
        print("")

        result = run_evaluation(
            state_path=str(state_path),
            checks=checks,
        )

        # Print report
        report = format_console_report(result)
        print(report)

        # Save JSON if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))

            print(f"\n💾 Report saved to: {output_path}")

        # Return appropriate exit code
        return 0 if result.overall_status == "PASS" else 1

    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
