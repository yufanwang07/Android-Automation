from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping, Protocol

from .config import AppConfig
from .errors import AgentConfigurationError, ProviderRequestError


ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["tap", "input", "key", "wait", "success", "stop"],
        },
        "x": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "y": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "text": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "seconds": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["type", "x", "y", "text", "seconds", "reason"],
    "additionalProperties": False,
}


class ModelProvider(Protocol):
    name: str
    model: str

    def decide(self, prompt: str) -> str: ...


def _required_key(
    environment: Mapping[str, str],
    variable: str,
    provider: str,
) -> str:
    value = environment.get(variable)
    if not value:
        raise AgentConfigurationError(
            f"Set {variable} before using the {provider} provider."
        )
    return value


@dataclass
class GeminiProvider:
    client: Any
    model: str
    name: str = "gemini"

    @classmethod
    def create(
        cls,
        config: AppConfig,
        *,
        environment: Mapping[str, str] = os.environ,
    ) -> GeminiProvider:
        api_key = _required_key(environment, "GEMINI_API_KEY", "Gemini")
        try:
            from google import genai
        except ImportError as error:
            raise AgentConfigurationError(
                'Install Gemini support with: pip install -e ".[gemini]"'
            ) from error
        return cls(client=genai.Client(api_key=api_key), model=config.resolved_model)

    def decide(self, prompt: str) -> str:
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ACTION_SCHEMA,
                },
            )
        except Exception as error:
            raise ProviderRequestError(f"Gemini request failed: {error}") from error
        if not interaction.output_text:
            raise ProviderRequestError("Gemini returned no text output.")
        return interaction.output_text


@dataclass
class OpenAIProvider:
    client: Any
    model: str
    max_output_tokens: int = 512
    name: str = "openai"

    @classmethod
    def create(
        cls,
        config: AppConfig,
        *,
        environment: Mapping[str, str] = os.environ,
    ) -> OpenAIProvider:
        api_key = _required_key(environment, "OPENAI_API_KEY", "OpenAI")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise AgentConfigurationError(
                'Install OpenAI support with: pip install -e ".[openai]"'
            ) from error
        options: dict[str, Any] = {"api_key": api_key}
        if config.base_url:
            options["base_url"] = config.base_url
        return cls(
            client=OpenAI(**options),
            model=config.resolved_model,
            max_output_tokens=config.max_output_tokens,
        )

    def decide(self, prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                max_output_tokens=self.max_output_tokens,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "android_ui_action",
                        "strict": True,
                        "schema": ACTION_SCHEMA,
                    }
                },
            )
        except Exception as error:
            raise ProviderRequestError(f"OpenAI request failed: {error}") from error
        if not response.output_text:
            raise ProviderRequestError("OpenAI returned no text output.")
        return response.output_text


@dataclass
class AnthropicProvider:
    client: Any
    model: str
    max_output_tokens: int = 512
    name: str = "anthropic"

    @classmethod
    def create(
        cls,
        config: AppConfig,
        *,
        environment: Mapping[str, str] = os.environ,
    ) -> AnthropicProvider:
        api_key = _required_key(environment, "ANTHROPIC_API_KEY", "Anthropic")
        try:
            from anthropic import Anthropic
        except ImportError as error:
            raise AgentConfigurationError(
                'Install Anthropic support with: pip install -e ".[anthropic]"'
            ) from error
        options: dict[str, Any] = {"api_key": api_key}
        if config.base_url:
            options["base_url"] = config.base_url
        return cls(
            client=Anthropic(**options),
            model=config.resolved_model,
            max_output_tokens=config.max_output_tokens,
        )

    def decide(self, prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": ACTION_SCHEMA,
                    }
                },
            )
        except Exception as error:
            raise ProviderRequestError(f"Anthropic request failed: {error}") from error
        if response.stop_reason == "refusal":
            raise ProviderRequestError("Anthropic refused the requested action.")
        text_blocks = [
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ]
        if not text_blocks:
            raise ProviderRequestError("Anthropic returned no text output.")
        return "".join(text_blocks)


PROVIDER_TYPES = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def create_provider(
    config: AppConfig,
    *,
    environment: Mapping[str, str] = os.environ,
) -> ModelProvider:
    return PROVIDER_TYPES[config.provider].create(config, environment=environment)
