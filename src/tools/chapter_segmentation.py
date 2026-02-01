from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Pattern

from .models import (
    BookSegmentationMetadata,
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
        compiled_book_patterns: List[Pattern[str]] = [
            re.compile(pattern, re.MULTILINE) for pattern in request.book_patterns
        ]

        # Find all chapter boundaries
        chapter_starts: List[tuple[int, str]] = []  # (line_number, title)
        book_starts: List[tuple[int, str]] = []  # (line_number, title)

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            for pattern in compiled_book_patterns:
                if pattern.match(stripped):
                    book_starts.append((line_num, stripped))
                    break

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

        # Determine book boundaries (use a single synthetic book if none detected)
        if not book_starts:
            book_starts = [(1, "BOOK 1")]
        else:
            latest_by_title: dict[str, int] = {}
            for line_num, title in book_starts:
                latest_by_title[title] = line_num
            book_starts = sorted(
                [(line_num, title) for title, line_num in latest_by_title.items()],
                key=lambda item: item[0],
            )

        books: List[BookSegmentationMetadata] = []
        chapters: List[ChapterSegmentationMetadata] = []

        global_index = 0
        for book_idx, (book_start, book_title) in enumerate(book_starts):
            if book_idx + 1 < len(book_starts):
                book_end = book_starts[book_idx + 1][0] - 1
            else:
                book_end = total_lines

            book_chapter_starts = [
                (line_num, title)
                for line_num, title in chapter_starts
                if book_start <= line_num <= book_end
            ]

            book_chapters: List[ChapterSegmentationMetadata] = []
            for chapter_idx, (start_line, title) in enumerate(book_chapter_starts):
                if chapter_idx + 1 < len(book_chapter_starts):
                    end_line = book_chapter_starts[chapter_idx + 1][0] - 1
                else:
                    end_line = book_end

                line_count = end_line - start_line + 1
                chapter_number = chapter_idx + 1

                chapter_meta = ChapterSegmentationMetadata(
                    index=global_index,
                    title=title,
                    book_index=book_idx,
                    book_title=book_title,
                    chapter_number=chapter_number,
                    start_line=start_line,
                    end_line=end_line,
                    line_count=line_count,
                )
                book_chapters.append(chapter_meta)
                chapters.append(chapter_meta)
                global_index += 1

            books.append(
                BookSegmentationMetadata(
                    index=book_idx,
                    title=book_title,
                    start_line=book_start,
                    end_line=book_end,
                    line_count=book_end - book_start + 1,
                    chapters=book_chapters,
                )
            )

        return ChapterSegmentationResult(
            books=books,
            chapters=chapters,
            total_books=len(books),
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
        book_title = "BOOK 1"

        while current_line <= total_lines:
            end_line = min(current_line + fallback_line_count - 1, total_lines)
            line_count = end_line - current_line + 1

            chapters.append(
                ChapterSegmentationMetadata(
                    index=chapter_idx,
                    title=f"Section {chapter_idx + 1}",
                    book_index=0,
                    book_title=book_title,
                    chapter_number=chapter_idx + 1,
                    start_line=current_line,
                    end_line=end_line,
                    line_count=line_count,
                )
            )

            current_line = end_line + 1
            chapter_idx += 1

        books = [
            BookSegmentationMetadata(
                index=0,
                title=book_title,
                start_line=1,
                end_line=total_lines,
                line_count=total_lines,
                chapters=chapters,
            )
        ]

        return ChapterSegmentationResult(
            books=books,
            chapters=chapters,
            total_books=len(books),
            total_chapters=len(chapters),
            total_lines=total_lines,
            fallback_used=True,
        )
