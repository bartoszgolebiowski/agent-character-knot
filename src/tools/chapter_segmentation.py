from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Pattern

from .models import (
    ChapterSegmentationMetadata,
    ChapterSegmentationRequest,
    ChapterSegmentationResult,
)


@dataclass(frozen=True, slots=True)
class ChapterSegmentationTool:
    """Deterministic tool for detecting chapter boundaries in text files (FR-02).

    This tool uses regex pattern matching to identify chapter headers and
    compute their line boundaries. It's designed to be fast, reproducible,
    and work without LLM calls.
    """

    def segment(self, request: ChapterSegmentationRequest) -> ChapterSegmentationResult:
        """Segment a text file into chapters based on header patterns.

        Args:
            request: Contains file path and regex patterns to match

        Returns:
            ChapterSegmentationResult with list of chapter metadata
        """
        file_path = Path(request.file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        # Read all lines from the file
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Compile regex patterns
        compiled_patterns: List[Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in request.patterns
        ]

        # Find all chapter boundaries
        chapter_starts: List[tuple[int, str]] = []  # (line_number, title)

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            for pattern in compiled_patterns:
                if pattern.match(stripped):
                    chapter_starts.append((line_num, stripped))
                    break

        # Handle case where no chapters are detected
        if not chapter_starts:
            # Use fallback: split by fixed line count
            return self._apply_fallback(
                lines=lines,
                total_lines=total_lines,
                fallback_line_count=request.fallback_line_count,
            )

        # Build chapter metadata with boundaries
        chapters: List[ChapterSegmentationMetadata] = []

        for idx, (start_line, title) in enumerate(chapter_starts):
            # End line is the line before the next chapter starts, or EOF
            if idx + 1 < len(chapter_starts):
                end_line = chapter_starts[idx + 1][0] - 1
            else:
                end_line = total_lines

            line_count = end_line - start_line + 1

            chapters.append(
                ChapterSegmentationMetadata(
                    index=idx,
                    title=title,
                    start_line=start_line,
                    end_line=end_line,
                    line_count=line_count,
                )
            )

        return ChapterSegmentationResult(
            chapters=chapters,
            total_chapters=len(chapters),
            total_lines=total_lines,
            fallback_used=False,
        )

    def _apply_fallback(
        self,
        lines: List[str],
        total_lines: int,
        fallback_line_count: int,
    ) -> ChapterSegmentationResult:
        """Apply fallback segmentation when no chapter markers are detected.

        Splits the text into fixed-size chunks.
        """
        chapters: List[ChapterSegmentationMetadata] = []
        current_line = 1
        chapter_idx = 0

        while current_line <= total_lines:
            end_line = min(current_line + fallback_line_count - 1, total_lines)
            line_count = end_line - current_line + 1

            chapters.append(
                ChapterSegmentationMetadata(
                    index=chapter_idx,
                    title=f"Section {chapter_idx + 1}",
                    start_line=current_line,
                    end_line=end_line,
                    line_count=line_count,
                )
            )

            current_line = end_line + 1
            chapter_idx += 1

        return ChapterSegmentationResult(
            chapters=chapters,
            total_chapters=len(chapters),
            total_lines=total_lines,
            fallback_used=True,
        )
