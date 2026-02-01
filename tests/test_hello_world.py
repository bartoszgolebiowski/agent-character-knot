from __future__ import annotations

from src.tools.hello_world import HelloWorldClient
from src.tools.models import HelloWorldRequest


def test_hello_world_returns_message() -> None:
    client = HelloWorldClient()
    result = client.call(HelloWorldRequest(query="Test"))

    assert result.message == "Hello, you sent: Test"
