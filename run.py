#!/usr/bin/env python3
"""Run Android Automation, repairing its local runtime when necessary."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import setup as project_setup


ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Load simple KEY=VALUE entries without overriding the current environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def execute(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            str(project_setup.venv_python()),
            "-m",
            "android_automation",
            *arguments,
        ],
        cwd=ROOT,
    )


def main(arguments: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if arguments is None else arguments
    load_dotenv()
    try:
        if not project_setup.runtime_is_ready():
            print("Runtime is missing or incomplete; running setup.py.")
            project_setup.ensure_runtime()

        result = execute(arguments)
        if result.returncode == 0:
            return 0

        # Exit code 127 means the installed command could not be loaded. Repair
        # once, then preserve the application's second exit code.
        if result.returncode == 127:
            print("Runtime failed to start; repairing with setup.py.")
            project_setup.ensure_runtime(force=True)
            return execute(arguments).returncode
        return result.returncode
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Could not run Android Automation: {error}", file=sys.stderr)
        return getattr(error, "returncode", 1)


if __name__ == "__main__":
    raise SystemExit(main())
