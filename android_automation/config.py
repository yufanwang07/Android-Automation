from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

from .errors import AgentConfigurationError


DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash",
    "openai": "gpt-5.4-mini",
    "anthropic": "claude-sonnet-4-6",
}
SUPPORTED_PROVIDERS = tuple(DEFAULT_MODELS)


def default_config_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.getenv("APPDATA", Path.home()))
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "android-automation" / "config.json"


@dataclass(frozen=True)
class AppConfig:
    provider: str = "gemini"
    model: str | None = None
    max_steps: int = 20
    step_delay_seconds: float = 0.5
    max_output_tokens: int = 512
    base_url: str | None = None

    @property
    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS[self.provider]

    def validate(self) -> AppConfig:
        if self.provider not in SUPPORTED_PROVIDERS:
            available = ", ".join(SUPPORTED_PROVIDERS)
            raise AgentConfigurationError(
                f"Unknown provider '{self.provider}'. Choose one of: {available}."
            )
        if self.max_steps < 1:
            raise AgentConfigurationError("max_steps must be positive.")
        if not 0 <= self.step_delay_seconds <= 30:
            raise AgentConfigurationError(
                "step_delay_seconds must be between 0 and 30."
            )
        if self.max_output_tokens < 64:
            raise AgentConfigurationError("max_output_tokens must be at least 64.")
        return self

    def to_dict(self) -> dict[str, Any]:
        output = asdict(self)
        output["model"] = self.resolved_model
        return output


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AgentConfigurationError(f"Could not read config file {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AgentConfigurationError(f"Config file {path} must contain a JSON object.")
    return payload


def _environment_values(environment: Mapping[str, str]) -> dict[str, Any]:
    mapping = {
        "provider": environment.get("ANDROID_AUTOMATION_PROVIDER"),
        "model": environment.get("ANDROID_AUTOMATION_MODEL"),
        "max_steps": environment.get("ANDROID_AUTOMATION_MAX_STEPS"),
        "step_delay_seconds": environment.get("ANDROID_AUTOMATION_STEP_DELAY"),
        "max_output_tokens": environment.get("ANDROID_AUTOMATION_MAX_OUTPUT_TOKENS"),
        "base_url": environment.get("ANDROID_AUTOMATION_BASE_URL"),
    }
    return {key: value for key, value in mapping.items() if value not in (None, "")}


def load_config(
    path: str | Path | None = None,
    *,
    overrides: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] = os.environ,
) -> AppConfig:
    configured_path = path or environment.get("ANDROID_AUTOMATION_CONFIG")
    selected_path = Path(configured_path).expanduser() if configured_path else None

    values: dict[str, Any] = {}
    if selected_path:
        values.update(_read_config_file(selected_path))
    else:
        project_path = Path.cwd() / ".android-automation.json"
        values.update(
            _read_config_file(
                project_path if project_path.exists() else default_config_path()
            )
        )
    values.update(_environment_values(environment))
    values.update(
        {
            key: value
            for key, value in (overrides or {}).items()
            if value is not None
        }
    )

    try:
        config = AppConfig(
            provider=str(values.get("provider", "gemini")).lower(),
            model=values.get("model"),
            max_steps=int(values.get("max_steps", 20)),
            step_delay_seconds=float(values.get("step_delay_seconds", 0.5)),
            max_output_tokens=int(values.get("max_output_tokens", 512)),
            base_url=values.get("base_url"),
        )
    except (TypeError, ValueError) as error:
        raise AgentConfigurationError(f"Invalid configuration value: {error}") from error
    return config.validate()


def write_config(config: AppConfig, path: str | Path | None = None) -> Path:
    destination = Path(path).expanduser() if path else default_config_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(config.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return destination
