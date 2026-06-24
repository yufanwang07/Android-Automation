#!/usr/bin/env python3
"""Bootstrap Android Automation and run it.

This file intentionally uses only the Python standard library so it can create
the project's virtual environment before any project dependency is installed.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
MARKER = VENV / ".android-automation-install"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def installation_fingerprint() -> str:
    inputs = [ROOT / "pyproject.toml"]
    digest = hashlib.sha256()
    for path in inputs:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_checked(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def compatible_python_command() -> list[str]:
    if sys.version_info >= (3, 10):
        return [sys.executable]

    candidates = [
        [path]
        for name in ("python3.13", "python3.12", "python3.11", "python3.10", "python3")
        if (path := shutil.which(name))
    ]
    if os.name == "nt" and shutil.which("py"):
        candidates = [
            ["py", version]
            for version in ("-3.13", "-3.12", "-3.11", "-3.10")
        ] + candidates

    for command in candidates:
        result = subprocess.run(
            [
                *command,
                "-c",
                "import sys; raise SystemExit(sys.version_info < (3, 10))",
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            return command
    raise SystemExit(
        "Python 3.10 or newer is required. Install it from https://python.org "
        "and run this file again."
    )


def bootstrap() -> Path:
    python = venv_python()
    if not python.exists():
        run_checked([*compatible_python_command(), "-m", "venv", str(VENV)])

    fingerprint = installation_fingerprint()
    installed = MARKER.read_text().strip() if MARKER.exists() else ""
    if installed != fingerprint:
        run_checked([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run_checked([str(python), "-m", "pip", "install", "-e", ".[all]"])
        MARKER.write_text(fingerprint + "\n")
    return python


def main() -> int:
    try:
        python = bootstrap()
        command = [str(python), "-m", "android_automation", *sys.argv[1:]]
        return subprocess.run(command, cwd=ROOT).returncode
    except subprocess.CalledProcessError as error:
        print(f"Setup failed with exit code {error.returncode}.", file=sys.stderr)
        return error.returncode


if __name__ == "__main__":
    raise SystemExit(main())
