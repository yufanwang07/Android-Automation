#!/usr/bin/env python3
"""Install and repair Android Automation's local runtime."""

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
REQUIRED_MODULES = ("android_automation", "google.genai", "openai", "anthropic")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def installation_fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update((ROOT / "pyproject.toml").read_bytes())
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
    raise RuntimeError(
        "Python 3.10 or newer is required. Install it from https://python.org "
        "and run setup.py again."
    )


def runtime_is_ready() -> bool:
    python = venv_python()
    if not python.exists() or not MARKER.exists():
        return False
    if MARKER.read_text(encoding="utf-8").strip() != installation_fingerprint():
        return False

    imports = "; ".join(f"import {module}" for module in REQUIRED_MODULES)
    result = subprocess.run(
        [str(python), "-c", imports],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        return False

    dependencies = subprocess.run(
        [str(python), "-m", "pip", "check"],
        cwd=ROOT,
        capture_output=True,
    )
    return dependencies.returncode == 0


def install(*, force: bool = False) -> Path:
    python = venv_python()
    if force and VENV.exists():
        shutil.rmtree(VENV)
    if not python.exists():
        run_checked([*compatible_python_command(), "-m", "venv", str(VENV)])

    run_checked([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run_checked([str(python), "-m", "pip", "install", "-e", ".[all]"])
    run_checked([str(python), "-m", "pip", "check"])
    MARKER.write_text(installation_fingerprint() + "\n", encoding="utf-8")
    return python


def ensure_runtime(*, force: bool = False) -> Path:
    if not force and runtime_is_ready():
        print("Android Automation is already set up.")
        return venv_python()
    return install(force=force)


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    unknown = [argument for argument in arguments if argument != "--force"]
    if unknown:
        print(f"Unknown setup option: {unknown[0]}", file=sys.stderr)
        return 2
    try:
        ensure_runtime(force="--force" in arguments)
        print("Setup complete.")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return getattr(error, "returncode", 1)


def is_packaging_invocation(arguments: list[str]) -> bool:
    # The user-facing script accepts only no arguments or --force. Every other
    # invocation belongs to setuptools, including evolving internal commands.
    return bool(arguments) and arguments != ["--force"]


if __name__ == "__main__":
    if is_packaging_invocation(sys.argv[1:]):
        # Setuptools still executes a root setup.py for parts of editable-build
        # compatibility, even when pyproject.toml is authoritative.
        from setuptools import setup as setuptools_setup

        setuptools_setup()
    else:
        raise SystemExit(main())
