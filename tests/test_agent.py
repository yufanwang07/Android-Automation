import unittest

from android_automation.agent import AgentAction, ActionType


class AgentActionTests(unittest.TestCase):
    def test_agent_action_parses_allowlisted_action(self) -> None:
        action = AgentAction.from_json(
            '{"type":"tap","x":120,"y":240,"reason":"Open settings"}'
        )
        self.assertIs(action.type, ActionType.TAP)
        self.assertEqual((action.x, action.y), (120, 240))

    def test_agent_action_rejects_unknown_action(self) -> None:
        with self.assertRaises(ValueError):
            AgentAction.from_json('{"type":"shell","text":"rm -rf /"}')

    def test_agent_action_requires_tap_coordinates(self) -> None:
        with self.assertRaisesRegex(ValueError, "require x and y"):
            AgentAction.from_json('{"type":"tap"}')


if __name__ == "__main__":
    unittest.main()
