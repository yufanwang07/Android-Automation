from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
from typing import Callable, Sequence

from .errors import AdbCommandError, AdbNotFoundError, DeviceSelectionError


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    details: tuple[str, ...] = ()

    @property
    def online(self) -> bool:
        return self.state == "device"


Runner = Callable[..., subprocess.CompletedProcess]


class AdbClient:
    """Small, injectable wrapper around the ADB executable."""

    def __init__(
        self,
        serial: str | None = None,
        *,
        adb_path: str = "adb",
        runner: Runner = subprocess.run,
    ) -> None:
        self.serial = serial or os.getenv("ANDROID_AUTOMATION_DEVICE")
        self.adb_path = adb_path
        self._runner = runner

    def _base_command(self, *, include_device: bool = True) -> list[str]:
        command = [self.adb_path]
        if include_device and self.serial:
            command.extend(["-s", self.serial])
        return command

    def _ensure_adb_available(self) -> None:
        if shutil.which(self.adb_path) is None and self._runner is subprocess.run:
            raise AdbNotFoundError(
                f"ADB executable '{self.adb_path}' was not found on PATH."
            )

    def run(
        self,
        *args: str,
        include_device: bool = True,
        binary: bool = False,
        check: bool = True,
    ) -> CommandResult:
        command = self._base_command(include_device=include_device) + list(args)
        self._ensure_adb_available()

        completed = self._runner(
            command,
            capture_output=True,
            text=not binary,
            check=False,
        )
        stdout = completed.stdout if not binary else ""
        stderr = completed.stderr if not binary else ""
        result = CommandResult(
            args=tuple(command),
            returncode=completed.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
        )
        if check and result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AdbCommandError(f"ADB command failed: {detail}")
        return result

    def devices(self) -> list[Device]:
        output = self.run("devices", "-l", include_device=False).stdout
        devices: list[Device] = []
        for line in output.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 2:
                devices.append(
                    Device(serial=fields[0], state=fields[1], details=tuple(fields[2:]))
                )
        return devices

    def selected(self) -> AdbClient:
        if self.serial:
            return self

        online = [device for device in self.devices() if device.online]
        if not online:
            raise DeviceSelectionError("No online Android devices were found.")
        if len(online) > 1:
            serials = ", ".join(device.serial for device in online)
            raise DeviceSelectionError(
                f"Multiple devices are online ({serials}); pass --device."
            )
        return AdbClient(
            serial=online[0].serial,
            adb_path=self.adb_path,
            runner=self._runner,
        )

    def shell(self, *args: str) -> str:
        return self.selected().run("shell", *args).stdout

    def launch(self, package: str, activity: str | None = None) -> str:
        if activity:
            component = activity if "/" in activity else f"{package}/{activity}"
            return self.shell("am", "start", "-n", component)
        return self.shell("monkey", "-p", package, "1")

    def clear_app_data(self, package: str) -> str:
        return self.shell("pm", "clear", package)

    def tap(self, x: int, y: int) -> None:
        self.shell("input", "tap", str(x), str(y))

    def input_text(self, text: str) -> None:
        encoded = text.replace("%", r"\%").replace(" ", "%s")
        self.shell("input", "text", encoded)

    def keyevent(self, key: str) -> None:
        normalized = key if key.startswith("KEYCODE_") else f"KEYCODE_{key.upper()}"
        self.shell("input", "keyevent", normalized)

    def dump_ui_xml(self) -> str:
        client = self.selected()
        client.shell("uiautomator", "dump", "/sdcard/window_dump.xml")
        return client.shell("cat", "/sdcard/window_dump.xml")

    def screenshot(self, destination: str | Path) -> Path:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        client = self.selected()
        client._ensure_adb_available()
        command = client._base_command() + ["exec-out", "screencap", "-p"]
        completed = client._runner(
            command,
            capture_output=True,
            text=False,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or b"").decode(errors="replace").strip()
            raise AdbCommandError(f"Could not capture screenshot: {detail}")
        path.write_bytes(completed.stdout)
        return path

    def run_shell_command(self, arguments: Sequence[str]) -> str:
        if not arguments:
            raise ValueError("At least one shell argument is required.")
        return self.shell(*arguments)
