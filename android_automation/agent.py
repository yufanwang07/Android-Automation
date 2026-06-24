from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import time

from .adb import AdbClient
from .providers import ModelProvider


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


class UiAgent:
    def __init__(
        self,
        adb: AdbClient,
        provider: ModelProvider,
        *,
        max_steps: int = 20,
        step_delay_seconds: float = 0.5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive.")
        self.adb = adb.selected()
        self.provider = provider
        self.max_steps = max_steps
        self.step_delay_seconds = step_delay_seconds

    def run(self, goal: str) -> AgentAction:
        previous = "No previous action."
        for step in range(1, self.max_steps + 1):
            xml = self.adb.dump_ui_xml()
            action = AgentAction.from_json(
                self.provider.decide(self._prompt(goal, xml, step, previous))
            )
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

            time.sleep(self.step_delay_seconds)
        return AgentAction(
            type=ActionType.STOP,
            reason=f"Stopped after the {self.max_steps}-step limit.",
        )

    @staticmethod
    def _prompt(goal: str, xml: str, step: int, previous: str) -> str:
        return f"""You control an Android device through a restricted action interface.

Goal:
{goal}

Choose exactly one safe next action. Mark success only when the goal is visibly
complete. Mark stop when safe progress is impossible. Do not suggest shell
commands or actions outside the available response contract.

Step: {step}
Previous action: {previous}

Current UIAutomator XML:
{xml}"""
