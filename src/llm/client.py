from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import LLMConfig
from .exceptions import LLMCallError, LLMConfigurationError

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass(slots=True)
class LLMClient:
    """Thin wrapper around OpenRouter's OpenAI-compatible API."""

    config: LLMConfig
    _client: Optional[OpenAI] = None

    def __post_init__(self) -> None:
        if not self.config.api_key:
            raise LLMConfigurationError("LLMConfig.api_key must be provided")
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.api_key, base_url=self.config.base_url
            )

    @classmethod
    def from_env(cls) -> "LLMClient":
        """Convenience constructor that loads configuration from env variables."""

        return cls(config=LLMConfig.from_env())

    def invoke(self, *, prompt: str, output_model: Type[TModel]) -> TModel:
        """Execute the provided prompt and parse it into the expected model."""

        try:
            response = self._client.responses.parse(  # type: ignore[union-attr]
                model=self.config.model,
                input=prompt,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
                text_format=output_model,
            )
        except Exception as exc:  # pragma: no cover - network errors
            print(f"LLM invocation error: {exc}")
            raise LLMCallError("Failed to execute LLM call") from exc

        payload = response.output_parsed
        try:
            return output_model.model_validate(payload)
        except ValidationError as exc:
            raise LLMCallError("LLM response failed schema validation") from exc
