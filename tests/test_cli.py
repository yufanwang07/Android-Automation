from contextlib import redirect_stdout
from io import StringIO
import unittest

from android_automation.cli import run


class CliTests(unittest.TestCase):
    def test_empty_command_shows_minimal_landing(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(run([]), 0)
        self.assertTrue(output.getvalue().startswith("Android Automation\n"))
        self.assertIn("devices", output.getvalue())
        self.assertNotIn("\x1b[", output.getvalue())

    def test_devices_command_prints_plain_table(self) -> None:
        class Device:
            serial = "emulator-5554"
            state = "device"

        class FakeAdb:
            def devices(self):
                return [Device()]

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(["devices"], adb=FakeAdb()), 0)
        self.assertEqual(output.getvalue(), "emulator-5554\tdevice\n")

    def test_providers_lists_defaults(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(["providers"]), 0)
        self.assertIn("gemini\tgemini-3.5-flash", output.getvalue())
        self.assertIn("openai\tgpt-5.4-mini", output.getvalue())
        self.assertIn("anthropic\tclaude-sonnet-4-6", output.getvalue())


if __name__ == "__main__":
    unittest.main()
