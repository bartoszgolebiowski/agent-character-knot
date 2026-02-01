from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Immutable configuration for the OpenRouter-powered LLM client."""

    api_key: str
    model: str = "openai/gpt-oss-120b"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.2
    max_output_tokens: int = 1200

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Build a config object using standard environment variables."""

        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing OPENROUTER_API_KEY (or fallback OPENAI_API_KEY) for LLM client."
            )

        base_url = os.getenv("OPENROUTER_BASE_URL") or cls.base_url_default()
        model = os.getenv("OPENROUTER_MODEL", cls.model_default())
        temperature = float(
            os.getenv("OPENROUTER_TEMPERATURE", cls.temperature_default())
        )
        max_output_tokens = int(
            os.getenv("OPENROUTER_MAX_OUTPUT_TOKENS", cls.max_output_tokens_default())
        )

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    @classmethod
    def base_url_default(cls) -> str:
        return "https://openrouter.ai/api/v1"

    @classmethod
    def model_default(cls) -> str:
        return "xiaomi/mimo-v2-flash:free"

    @classmethod
    def temperature_default(cls) -> float:
        return 0.2

    @classmethod
    def max_output_tokens_default(cls) -> int:
        return 1200
