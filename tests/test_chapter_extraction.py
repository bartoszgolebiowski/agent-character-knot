from __future__ import annotations

from pathlib import Path

from src.tools.chapter_extraction import ChapterExtractionTool
from src.tools.models import ChapterExtractionRequest, ChapterSegmentationMetadata


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_chapter_extraction_reads_only_requested_lines(tmp_path: Path) -> None:
    book = tmp_path / "book.txt"
    _write_text(book, "A\nB\nC\nD\nE\n")

    chapter_map = [
        ChapterSegmentationMetadata(
            index=0,
            title="Chapter 1",
            book_index=0,
            book_title="BOOK 1",
            chapter_number=1,
            start_line=1,
            end_line=2,
            line_count=2,
        ),
        ChapterSegmentationMetadata(
            index=1,
            title="Chapter 2",
            book_index=0,
            book_title="BOOK 1",
            chapter_number=2,
            start_line=3,
            end_line=5,
            line_count=3,
        ),
    ]

    tool = ChapterExtractionTool()
    result = tool.extract(
        ChapterExtractionRequest(
            file_path=str(book),
            chapter_index=1,
            chapter_map=chapter_map,
        )
    )

    assert result.chapter_index == 1
    assert result.chapter_title == "Chapter 2"
    assert result.text == "C\nD\nE\n"
    assert result.line_count == 3
    assert result.start_line == 3
    assert result.end_line == 5
