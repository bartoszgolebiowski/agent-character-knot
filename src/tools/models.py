from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.memory.models import ChapterMetadata


class ToolName(str, Enum):
    """Names of available tools."""

    HELLO_WORLD = "hello_world"
    CHAPTER_SEGMENTATION = "chapter_segmentation"
    CHAPTER_EXTRACTION = "chapter_extraction"
    HTML_REPORT_GENERATION = "html_report_generation"


# =============================================================================
# Hello World Tool Models
# =============================================================================


class HelloWorldRequest(BaseModel):
    """A simple request model for testing connectivity."""

    query: str


class HelloWorldResponse(BaseModel):
    """A simple response model for testing connectivity."""

    message: str


# =============================================================================
# Chapter Segmentation Tool Models (FR-02)
# =============================================================================


class ChapterSegmentationRequest(BaseModel):
    """Request to segment a book into chapters."""

    file_path: str = Field(description="Absolute path to the text file")
    patterns: List[str] = Field(
        default=[
            r"^CHAPTER\s+[IVXLCDM\d]+",  # Roman/Arabic numerals
            r"^PART\s+[IVXLCDM\d]+",
        ],
        description="Regex patterns to match chapter headers",
    )
    book_patterns: List[str] = Field(
        default=[
            r"^BOOK\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN):\s*.*$",
        ],
        description="Regex patterns to match book headers",
    )
    fallback_line_count: int = Field(
        default=1000,
        description="Number of lines per segment if no chapters detected",
    )


class ChapterSegmentationMetadata(BaseModel):
    """Metadata for a single chapter from segmentation."""

    index: int = Field(description="Zero-based chapter index")
    title: str = Field(description="Chapter title/header text")
    book_index: int = Field(description="Zero-based book index containing chapter")
    book_title: str = Field(description="Book title/header text")
    chapter_number: int = Field(
        description="1-based chapter number within the containing book"
    )
    start_line: int = Field(description="1-based line number where chapter starts")
    end_line: int = Field(description="1-based line number where chapter ends")
    line_count: int = Field(description="Total lines in this chapter")


class BookSegmentationMetadata(BaseModel):
    """Metadata for a single book and its chapters."""

    index: int = Field(description="Zero-based book index")
    title: str = Field(description="Book title/header text")
    start_line: int = Field(description="1-based line number where book starts")
    end_line: int = Field(description="1-based line number where book ends")
    line_count: int = Field(description="Total lines in this book section")
    chapters: List[ChapterSegmentationMetadata] = Field(
        default_factory=list,
        description="Chapters that belong to this book",
    )


class ChapterSegmentationResult(BaseModel):
    """Result of chapter segmentation."""

    books: List[BookSegmentationMetadata] = Field(
        default_factory=list,
        description="List of book metadata with nested chapters",
    )
    chapters: List[ChapterSegmentationMetadata] = Field(
        default_factory=list,
        description="List of chapter metadata",
    )
    total_books: int = Field(description="Total number of books detected")
    total_chapters: int = Field(description="Total number of chapters detected")
    total_lines: int = Field(description="Total number of lines in the file")
    fallback_used: bool = Field(
        default=False,
        description="True if no chapters detected and fallback applied",
    )


# =============================================================================
# Chapter Extraction Tool Models (FR-01)
# =============================================================================


class ChapterExtractionRequest(BaseModel):
    """Request to extract a specific chapter's text."""

    file_path: str = Field(description="Absolute path to the text file")
    chapter_index: int = Field(description="Zero-based chapter index to extract")
    chapter_map: List["ChapterSegmentationMetadata"] = Field(
        default_factory=list,
        description="Previously computed chapter boundaries",
    )


class ChapterExtractionResult(BaseModel):
    """Result of chapter extraction."""

    chapter_index: int = Field(description="Zero-based chapter index")
    chapter_title: str = Field(description="Chapter title")
    text: str = Field(description="Full text content of the chapter")
    line_count: int = Field(description="Number of lines in this chapter")
    start_line: int = Field(description="1-based starting line number")
    end_line: int = Field(description="1-based ending line number")


# =============================================================================
# HTML Report Generation Tool Models (FR-10, FR-11)
# =============================================================================


class HTMLReportRequest(BaseModel):
    """Request to generate HTML report."""

    output_directory: str = Field(
        description="Path where HTML files will be written",
    )
    report_title: str = Field(
        default="StoryGraph Character Analysis",
        description="Title for the report",
    )
    book_title: str = Field(description="Title of the analyzed book")


class HTMLReportResult(BaseModel):
    """Result of HTML report generation."""

    output_path: str = Field(description="Directory where files were written")
    files_generated: List[str] = Field(
        description="List of generated HTML file paths",
    )
    index_file: str = Field(description="Path to the index.html file")
    total_characters: int = Field(description="Number of character pages generated")
    total_chapters: int = Field(description="Number of chapter pages generated")
