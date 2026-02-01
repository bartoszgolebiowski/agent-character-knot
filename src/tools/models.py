from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ToolName(str, Enum):
    """Names of available tools."""

    HELLO_WORLD = "hello_world"


class HelloWorldRequest(BaseModel):
    """A simple request model for testing connectivity."""

    query: str


class HelloWorldResponse(BaseModel):
    """A simple response model for testing connectivity."""

    message: str
