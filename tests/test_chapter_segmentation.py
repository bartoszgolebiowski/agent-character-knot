from __future__ import annotations

import math

from src.tools.chapter_segmentation import ChapterSegmentationTool
from src.tools.models import ChapterSegmentationRequest


def test_chapter_segmentation_detects_books_and_chapters() -> None:
    tool = ChapterSegmentationTool()
    result = tool.segment(
        ChapterSegmentationRequest(file_path="static/war-and-peace-by-leo-tolstoy.txt")
    )

    assert result.fallback_used is False
    assert result.total_books == 15
    assert result.total_chapters == 374
    assert result.total_lines == 66036

    assert result.books[0].title == "BOOK ONE: 1805"
    assert result.books[0].start_line == 828
    assert result.books[-1].title == "BOOK FIFTEEN: 1812 - 13"
    assert result.books[-1].end_line == result.total_lines

    assert result.chapters[0].title == "CHAPTER I"
    assert result.chapters[0].book_index == 0
    assert result.chapters[0].chapter_number == 1
    assert result.chapters[-1].title == "CHAPTER XII"

    assert sum(len(book.chapters) for book in result.books) == result.total_chapters
    for book in result.books:
        assert book.chapters
        for chapter in book.chapters:
            assert (
                book.start_line
                <= chapter.start_line
                <= chapter.end_line
                <= book.end_line
            )


def test_chapter_segmentation_fallback_with_static_file() -> None:
    tool = ChapterSegmentationTool()
    result = tool.segment(
        ChapterSegmentationRequest(
            file_path="static/war-and-peace-by-leo-tolstoy.txt",
            patterns=[r"^NO_CHAPTER_HEADERS$"],
            fallback_line_count=5000,
        )
    )

    assert result.fallback_used is True
    assert result.total_books == 1
    assert result.total_lines == 66036
    assert result.total_chapters == math.ceil(result.total_lines / 5000)
