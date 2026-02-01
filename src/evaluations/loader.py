"""Markdown parser for quality check definitions.

This module implements the logic to parse Markdown files containing
quality check definitions in the specific format used by the leaderboard.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.evaluations.models import CheckDefinition, CheckPriority


def parse_leaderboard_markdown(file_path: str | Path) -> list[CheckDefinition]:
    """Parse a leaderboard Markdown file into CheckDefinition objects.

    The expected format is:
        #### LC-001 🔴 MUST-HAVE | Title
        - **Criterion**: Description of what is being checked
        - **Verification**: How to verify it
        - **Positive Example**: (optional) Good example
        - **Negative Example**: (optional) Bad example

    Args:
        file_path: Path to the Markdown file

    Returns:
        List of CheckDefinition objects

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the Markdown format is invalid
    """
    file_path = Path(file_path)
    if not file_path.exists():
        msg = f"Leaderboard file not found: {file_path}"
        raise FileNotFoundError(msg)

    content = file_path.read_text(encoding="utf-8")
    checks = []

    # Split content into sections by headers
    sections = re.split(r"####\s+([A-Z]{2,4}-\d{3})", content)

    # Process sections (skip first element which is content before first header)
    i = 1
    while i < len(sections):
        check_id = sections[i].strip()
        section_content = sections[i + 1] if i + 1 < len(sections) else ""

        # Extract priority and title from first line (emoji + priority | title)
        first_line = section_content.split("\n")[0].strip()
        first_line_match = re.search(
            r"(?:🔴|🟡|🟢)\s+(MUST-HAVE|SHOULD-HAVE|NICE-TO-HAVE)\s*\|\s*(.+)$",
            first_line,
        )

        if not first_line_match:
            i += 2
            continue

        priority_str = first_line_match.group(1)
        title = (first_line_match.group(2) or "").strip()

        # Parse priority
        try:
            priority = CheckPriority(priority_str)
        except ValueError:
            i += 2
            continue

        # Extract criterion
        criterion_match = re.search(
            r"-\s+\*\*Criterion\*\*:\s+(.+?)(?=\n-|\n\n|$)",
            section_content,
            re.DOTALL,
        )
        criterion = criterion_match.group(1).strip() if criterion_match else ""

        # Extract verification
        verification_match = re.search(
            r"-\s+\*\*Verification\*\*:\s+(.+?)(?=\n-|\n\n|$)",
            section_content,
            re.DOTALL,
        )
        verification = verification_match.group(1).strip() if verification_match else ""

        # Extract positive example (optional)
        positive_match = re.search(
            r"-\s+\*\*Positive Example\*\*:\s+(.+?)(?=\n-|\n\n|$)",
            section_content,
            re.DOTALL,
        )
        positive_example = positive_match.group(1).strip() if positive_match else None

        # Extract negative example (optional)
        negative_match = re.search(
            r"-\s+\*\*Negative Example\*\*:\s+(.+?)(?=\n-|\n\n|$)",
            section_content,
            re.DOTALL,
        )
        negative_example = negative_match.group(1).strip() if negative_match else None

        # Only create CheckDefinition if we have required fields
        if check_id and criterion and verification:
            check = CheckDefinition(
                check_id=check_id,
                priority=priority,
                title=title,
                criterion=criterion,
                verification=verification,
                positive_example=positive_example,
                negative_example=negative_example,
            )
            checks.append(check)

        i += 2

    if not checks:
        msg = f"No valid checks found in {file_path}"
        raise ValueError(msg)

    return checks
