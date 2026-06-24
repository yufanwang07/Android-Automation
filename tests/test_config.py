import json
from pathlib import Path
import tempfile
import unittest

from android_automation.config import AppConfig, load_config, write_config
from android_automation.errors import AgentConfigurationError


class ConfigTests(unittest.TestCase):
    def test_defaults_resolve_provider_model(self) -> None:
        config = load_config(
            Path("/does/not/exist.json"),
            environment={},
        )
        self.assertEqual(config.provider, "gemini")
        self.assertEqual(config.resolved_model, "gemini-3.5-flash")

    def test_environment_and_cli_override_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"provider": "gemini", "model": "file-model"}),
                encoding="utf-8",
            )
            config = load_config(
                path,
                environment={
                    "ANDROID_AUTOMATION_PROVIDER": "openai",
                    "ANDROID_AUTOMATION_MODEL": "environment-model",
                },
                overrides={"model": "cli-model"},
            )
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.resolved_model, "cli-model")

    def test_write_config_does_not_include_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = write_config(
                AppConfig(provider="anthropic"),
                Path(directory) / "config.json",
            )
            payload = destination.read_text(encoding="utf-8")
        self.assertNotIn("API_KEY", payload)
        self.assertIn("claude-sonnet-4-6", payload)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(AgentConfigurationError, "Unknown provider"):
            AppConfig(provider="unknown").validate()


if __name__ == "__main__":
    unittest.main()
