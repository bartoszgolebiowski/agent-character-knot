"""Tool definitions and adapters."""

from .chapter_extraction import ChapterExtractionTool
from .chapter_segmentation import ChapterSegmentationTool
from .hello_world import HelloWorldClient
from .html_report_generator import HTMLReportGeneratorTool
from .models import (
    ChapterExtractionRequest,
    ChapterExtractionResult,
    ChapterSegmentationMetadata,
    ChapterSegmentationRequest,
    ChapterSegmentationResult,
    HelloWorldRequest,
    HelloWorldResponse,
    HTMLReportRequest,
    HTMLReportResult,
    ToolName,
)

__all__ = [
    # Tool Names
    "ToolName",
    # Hello World
    "HelloWorldClient",
    "HelloWorldRequest",
    "HelloWorldResponse",
    # Chapter Segmentation
    "ChapterSegmentationTool",
    "ChapterSegmentationRequest",
    "ChapterSegmentationResult",
    "ChapterSegmentationMetadata",
    # Chapter Extraction
    "ChapterExtractionTool",
    "ChapterExtractionRequest",
    "ChapterExtractionResult",
    # HTML Report Generator
    "HTMLReportGeneratorTool",
    "HTMLReportRequest",
    "HTMLReportResult",
]
