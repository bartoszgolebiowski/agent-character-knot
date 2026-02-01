from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import (
    ChapterExtractionRequest,
    ChapterExtractionResult,
)


@dataclass(frozen=True, slots=True)
class ChapterExtractionTool:
    """Tool for extracting a single chapter's text from a file (FR-01).

    This tool loads only the specific chapter requested, making it memory
    efficient for processing large books. It requires the chapter map
    (from ChapterSegmentationTool) to know where to read.
    """

    def extract(self, request: ChapterExtractionRequest) -> ChapterExtractionResult:
        """Extract a specific chapter's text from a file.

        Args:
            request: Contains file path, chapter index, and chapter map

        Returns:
            ChapterExtractionResult with the chapter's full text

        Raises:
            FileNotFoundError: If the source file doesn't exist
            IndexError: If the chapter index is out of range
            ValueError: If the chapter map is empty
        """
        file_path = Path(request.file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        if not request.chapter_map:
            raise ValueError("Chapter map is empty. Run segmentation first.")

        if request.chapter_index < 0 or request.chapter_index >= len(
            request.chapter_map
        ):
            raise IndexError(
                f"Chapter index {request.chapter_index} out of range. "
                f"Book has {len(request.chapter_map)} chapters."
            )

        # Get the chapter metadata
        chapter_meta = request.chapter_map[request.chapter_index]
        start_line = chapter_meta.start_line
        end_line = chapter_meta.end_line

        # Read only the lines for this chapter (1-indexed in metadata)
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        # Extract the chapter lines (convert from 1-indexed to 0-indexed)
        chapter_lines = lines[start_line - 1 : end_line]
        chapter_text = "".join(chapter_lines)

        return ChapterExtractionResult(
            chapter_index=request.chapter_index,
            chapter_title=chapter_meta.title,
            text=chapter_text,
            line_count=len(chapter_lines),
            start_line=start_line,
            end_line=end_line,
        )
