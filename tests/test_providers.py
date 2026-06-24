from types import SimpleNamespace
import unittest

from android_automation.providers import (
    ACTION_SCHEMA,
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
)


ACTION_JSON = (
    '{"type":"wait","x":null,"y":null,"text":null,'
    '"seconds":1,"reason":"Loading"}'
)


class Recorder:
    def __init__(self, response) -> None:
        self.response = response
        self.arguments = None

    def create(self, **arguments):
        self.arguments = arguments
        return self.response


class ProviderTests(unittest.TestCase):
    def test_gemini_uses_interactions_structured_output(self) -> None:
        interactions = Recorder(SimpleNamespace(output_text=ACTION_JSON))
        client = SimpleNamespace(interactions=interactions)
        output = GeminiProvider(client=client, model="gemini-test").decide("prompt")
        self.assertEqual(output, ACTION_JSON)
        self.assertEqual(interactions.arguments["input"], "prompt")
        self.assertEqual(
            interactions.arguments["response_format"]["schema"],
            ACTION_SCHEMA,
        )

    def test_openai_uses_responses_text_format(self) -> None:
        responses = Recorder(SimpleNamespace(output_text=ACTION_JSON))
        client = SimpleNamespace(responses=responses)
        output = OpenAIProvider(client=client, model="gpt-test").decide("prompt")
        self.assertEqual(output, ACTION_JSON)
        self.assertFalse(responses.arguments["store"])
        self.assertEqual(responses.arguments["max_output_tokens"], 512)
        text_format = responses.arguments["text"]["format"]
        self.assertEqual(text_format["type"], "json_schema")
        self.assertTrue(text_format["strict"])
        self.assertEqual(text_format["schema"], ACTION_SCHEMA)

    def test_anthropic_uses_messages_output_config(self) -> None:
        block = SimpleNamespace(type="text", text=ACTION_JSON)
        messages = Recorder(
            SimpleNamespace(content=[block], stop_reason="end_turn")
        )
        client = SimpleNamespace(messages=messages)
        output = AnthropicProvider(
            client=client,
            model="claude-test",
        ).decide("prompt")
        self.assertEqual(output, ACTION_JSON)
        self.assertEqual(
            messages.arguments["output_config"]["format"]["schema"],
            ACTION_SCHEMA,
        )
        self.assertEqual(messages.arguments["messages"][0]["content"], "prompt")

    def test_action_schema_is_strict_and_provider_portable(self) -> None:
        self.assertFalse(ACTION_SCHEMA["additionalProperties"])
        self.assertEqual(
            set(ACTION_SCHEMA["required"]),
            set(ACTION_SCHEMA["properties"]),
        )


if __name__ == "__main__":
    unittest.main()
