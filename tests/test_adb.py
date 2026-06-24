from pathlib import Path
import subprocess
import tempfile
import unittest

from android_automation.adb import AdbClient


class FakeRunner:
    def __init__(self, responses: list[subprocess.CompletedProcess]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return self.responses.pop(0)


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class AdbClientTests(unittest.TestCase):
    def test_devices_parses_adb_output(self) -> None:
        runner = FakeRunner(
            [
                completed(
                    "List of devices attached\n"
                    "emulator-5554 device product:sdk model:Pixel\n"
                    "offline-1 offline\n"
                )
            ]
        )
        devices = AdbClient(runner=runner).devices()
        self.assertEqual(
            [(device.serial, device.state) for device in devices],
            [("emulator-5554", "device"), ("offline-1", "offline")],
        )
        self.assertEqual(runner.commands, [["adb", "devices", "-l"]])

    def test_single_online_device_is_selected_automatically(self) -> None:
        runner = FakeRunner(
            [
                completed("List of devices attached\nemulator-5554 device\n"),
                completed("Events injected: 1\n"),
            ]
        )
        output = AdbClient(runner=runner).launch("com.example")
        self.assertEqual(output, "Events injected: 1\n")
        self.assertEqual(
            runner.commands[-1],
            [
                "adb",
                "-s",
                "emulator-5554",
                "shell",
                "monkey",
                "-p",
                "com.example",
                "1",
            ],
        )

    def test_text_input_uses_adb_space_encoding(self) -> None:
        runner = FakeRunner([completed()])
        AdbClient(serial="device-1", runner=runner).input_text("hello world")
        self.assertEqual(runner.commands[-1][-2:], ["text", "hello%sworld"])

    def test_screenshot_writes_binary_output(self) -> None:
        runner = FakeRunner([completed(stdout=b"png-bytes", stderr=b"")])
        with tempfile.TemporaryDirectory() as directory:
            output = AdbClient(serial="device-1", runner=runner).screenshot(
                Path(directory) / "screen.png"
            )
            self.assertEqual(output.read_bytes(), b"png-bytes")
        self.assertEqual(runner.commands[-1][-3:], ["exec-out", "screencap", "-p"])


if __name__ == "__main__":
    unittest.main()
