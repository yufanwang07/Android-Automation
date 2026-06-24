from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
import time
from typing import Protocol

from .adb import AdbClient
from .errors import AgentConfigurationError


class ActionType(str, Enum):
    TAP = "tap"
    INPUT = "input"
    KEY = "key"
    WAIT = "wait"
    SUCCESS = "success"
    STOP = "stop"


@dataclass(frozen=True)
class AgentAction:
    type: ActionType
    x: int | None = None
    y: int | None = None
    text: str | None = None
    seconds: float = 1.0
    reason: str = ""

    @classmethod
    def from_json(cls, value: str) -> AgentAction:
        payload = json.loads(value)
        action = cls(
            type=ActionType(payload["type"]),
            x=payload.get("x"),
            y=payload.get("y"),
            text=payload.get("text"),
            seconds=float(payload.get("seconds", 1.0)),
            reason=payload.get("reason", ""),
        )
        action.validate()
        return action

    def validate(self) -> None:
        if self.type is ActionType.TAP and (self.x is None or self.y is None):
            raise ValueError("Tap actions require x and y coordinates.")
        if self.type in (ActionType.INPUT, ActionType.KEY) and not self.text:
            raise ValueError(f"{self.type.value} actions require text.")
        if self.type is ActionType.WAIT and not 0 <= self.seconds <= 30:
            raise ValueError("Wait duration must be between 0 and 30 seconds.")


class ModelProvider(Protocol):
    def decide(self, prompt: str) -> str: ...


class GeminiProvider:
    def __init__(self, client: object, model: str) -> None:
        self.client = client
        self.model = model

    @classmethod
    def from_environment(cls, model: str | None = None) -> GeminiProvider:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AgentConfigurationError("Set GEMINI_API_KEY before using the agent.")
        try:
            from google import genai
        except ImportError as error:
            raise AgentConfigurationError(
                'Install the optional dependency with: pip install -e ".[agent]"'
            ) from error
        return cls(
            client=genai.Client(api_key=api_key),
            model=model or os.getenv("ANDROID_AUTOMATION_MODEL", "gemini-2.5-flash"),
        )

    def decide(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return response.text


class UiAgent:
    def __init__(
        self,
        adb: AdbClient,
        provider: ModelProvider,
        *,
        max_steps: int = 20,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive.")
        self.adb = adb.selected()
        self.provider = provider
        self.max_steps = max_steps

    def run(self, goal: str) -> AgentAction:
        previous = "No previous action."
        for step in range(1, self.max_steps + 1):
            xml = self.adb.dump_ui_xml()
            prompt = self._prompt(goal, xml, step, previous)
            action = AgentAction.from_json(self.provider.decide(prompt))
            previous = action.reason or action.type.value

            if action.type is ActionType.TAP:
                self.adb.tap(action.x, action.y)  # type: ignore[arg-type]
            elif action.type is ActionType.INPUT:
                self.adb.input_text(action.text or "")
            elif action.type is ActionType.KEY:
                self.adb.keyevent(action.text or "")
            elif action.type is ActionType.WAIT:
                time.sleep(action.seconds)
            elif action.type in (ActionType.SUCCESS, ActionType.STOP):
                return action

            time.sleep(0.5)
        return AgentAction(
            type=ActionType.STOP,
            reason=f"Stopped after the {self.max_steps}-step limit.",
        )

    @staticmethod
    def _prompt(goal: str, xml: str, step: int, previous: str) -> str:
        return f"""Control the Android UI to complete this goal:
{goal}

Step: {step}
Previous action: {previous}
Current UIAutomator XML:
{xml}

Return exactly one JSON object:
{{
  "type": "tap" | "input" | "key" | "wait" | "success" | "stop",
  "x": integer required for tap,
  "y": integer required for tap,
  "text": string required for input or key,
  "seconds": number from 0 to 30 for wait,
  "reason": "short description"
}}

Use only the allowed action types. Never return a shell command. Use success only
when the goal is visibly complete, and stop when safe progress is impossible."""
