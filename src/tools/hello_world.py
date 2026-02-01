from __future__ import annotations

from dataclasses import dataclass

from .models import (
    HelloWorldRequest,
    HelloWorldResponse,
)


@dataclass(frozen=True, slots=True)
class HelloWorldClient:
    """Thin wrapper around the Tavily Search API."""

    def call(self, payload: HelloWorldRequest) -> HelloWorldResponse:
        """Call the Hello World API endpoint."""
        # This is a mock implementation for demonstration purposes.
        response_message = f"Hello, you sent: {payload.query}"
        return HelloWorldResponse(message=response_message)
