from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Sequence

from .adb import AdbClient
from .agent import UiAgent
from .config import (
    AppConfig,
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    default_config_path,
    load_config,
    write_config,
)
from .errors import AndroidAutomationError
from .providers import create_provider
from .ui import UiHierarchy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="android-automation",
        description="Minimal Android automation through ADB.",
    )
    parser.add_argument("--device", help="ADB device serial")
    parser.add_argument("--config", type=Path, help="JSON configuration file")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("devices", help="List connected devices")
    subparsers.add_parser("providers", help="List supported AI providers")
    subparsers.add_parser("doctor", help="Check local setup and configuration")

    config_parser = subparsers.add_parser("config", help="View or create configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show resolved configuration")
    config_init = config_subparsers.add_parser("init", help="Write a configuration file")
    config_init.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="gemini",
    )
    config_init.add_argument("--model")
    config_init.add_argument("--output", type=Path)
    config_init.add_argument("--force", action="store_true")

    launch = subparsers.add_parser("launch", help="Launch an Android app")
    launch.add_argument("package")
    launch.add_argument("--activity")

    clear = subparsers.add_parser("clear", help="Clear an app's local data")
    clear.add_argument("package")

    screenshot = subparsers.add_parser("screenshot", help="Save a PNG screenshot")
    screenshot.add_argument("output", type=Path)

    dump = subparsers.add_parser("dump-ui", help="Print the current UI hierarchy")
    dump.add_argument("--clickable", action="store_true")
    dump.add_argument("--xml", action="store_true", help="Print raw XML")

    find = subparsers.add_parser("find", help="Find UI nodes by label or resource ID")
    find.add_argument("--text", required=True)

    tap = subparsers.add_parser("tap", help="Tap screen coordinates")
    tap.add_argument("x", type=int)
    tap.add_argument("y", type=int)

    input_parser = subparsers.add_parser("input", help="Type text")
    input_parser.add_argument("text")

    key = subparsers.add_parser("key", help="Send an Android key event")
    key.add_argument("name")

    shell = subparsers.add_parser("shell", help="Run an explicit ADB shell command")
    shell.add_argument("arguments", nargs=argparse.REMAINDER)

    agent = subparsers.add_parser("agent", help="Run optional goal-driven automation")
    agent.add_argument("goal")
    agent.add_argument("--provider", choices=SUPPORTED_PROVIDERS)
    agent.add_argument("--model")
    agent.add_argument("--max-steps", type=int)

    return parser


def print_landing(parser: argparse.ArgumentParser) -> None:
    print("Android Automation")
    print()
    print("  devices            list connected devices")
    print("  launch PACKAGE     launch an app")
    print("  screenshot FILE    save the current screen")
    print("  dump-ui            inspect the current UI")
    print("  agent GOAL         run goal-driven automation")
    print("  doctor             check setup and configuration")
    print()
    print(f"Run '{parser.prog} --help' for all commands.")


def _print_nodes(hierarchy: UiHierarchy, *, clickables: bool = False) -> None:
    nodes = hierarchy.clickables() if clickables else hierarchy.visible()
    if not nodes:
        print("No matching UI nodes.")
        return
    for node in nodes:
        print(node.summary())


def _agent_config(args: argparse.Namespace) -> AppConfig:
    return load_config(
        args.config,
        overrides={
            "provider": args.provider,
            "model": args.model,
            "max_steps": args.max_steps,
        },
    )


def _doctor(config_path: Path | None) -> int:
    config = load_config(config_path)
    checks = [
        ("Python", sys.version.split()[0], sys.version_info >= (3, 10)),
        ("ADB", shutil.which("adb") or "not found", shutil.which("adb") is not None),
    ]
    module_names = {
        "gemini": "google.genai",
        "openai": "openai",
        "anthropic": "anthropic",
    }
    module = module_names[config.provider]
    try:
        module_installed = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError):
        module_installed = False
    checks.append(
        (
            f"{config.provider} SDK",
            "installed" if module_installed else "not installed",
            module_installed,
        )
    )
    key_names = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    key_name = key_names[config.provider]
    checks.append(
        (
            key_name,
            "set" if os.getenv(key_name) else "not set",
            bool(os.getenv(key_name)),
        )
    )

    for label, detail, passed in checks:
        print(f"{'ok' if passed else 'missing'}\t{label}\t{detail}")
    print(f"provider\t{config.provider}\t{config.resolved_model}")
    return 0 if all(check[2] for check in checks) else 1


def run(arguments: Sequence[str], *, adb: AdbClient | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    if not args.command:
        print_landing(parser)
        return 0

    client = adb or AdbClient(serial=args.device)

    if args.command == "devices":
        for device in client.devices():
            print(f"{device.serial}\t{device.state}")
        return 0
    if args.command == "providers":
        for provider in SUPPORTED_PROVIDERS:
            print(f"{provider}\t{DEFAULT_MODELS[provider]}")
        return 0
    if args.command == "doctor":
        return _doctor(args.config)
    if args.command == "config":
        if args.config_command == "show":
            print(json.dumps(load_config(args.config).to_dict(), indent=2))
            return 0
        if args.config_command == "init":
            destination = args.output or args.config or default_config_path()
            if destination.exists() and not args.force:
                raise ValueError(
                    f"{destination} already exists; pass --force to replace it."
                )
            config = AppConfig(provider=args.provider, model=args.model).validate()
            print(write_config(config, destination))
            return 0
        parser.error("config requires 'show' or 'init'")

    if args.command == "launch":
        output = client.launch(args.package, args.activity)
    elif args.command == "clear":
        output = client.clear_app_data(args.package)
    elif args.command == "screenshot":
        print(client.screenshot(args.output))
        return 0
    elif args.command in ("dump-ui", "find"):
        hierarchy = UiHierarchy.parse(client.dump_ui_xml())
        if args.command == "find":
            matches = hierarchy.find(args.text)
            for node in matches:
                print(node.summary())
            return 0 if matches else 1
        if args.xml:
            print(hierarchy.raw_xml)
        else:
            _print_nodes(hierarchy, clickables=args.clickable)
        return 0
    elif args.command == "tap":
        client.tap(args.x, args.y)
        return 0
    elif args.command == "input":
        client.input_text(args.text)
        return 0
    elif args.command == "key":
        client.keyevent(args.name)
        return 0
    elif args.command == "shell":
        output = client.run_shell_command(args.arguments)
    elif args.command == "agent":
        config = _agent_config(args)
        provider = create_provider(config)
        result = UiAgent(
            client,
            provider,
            max_steps=config.max_steps,
            step_delay_seconds=config.step_delay_seconds,
        ).run(args.goal)
        print(result.reason or result.type.value)
        return 0 if result.type.value == "success" else 1
    else:
        parser.error(f"Unsupported command: {args.command}")
        return 2

    if output.strip():
        print(output.strip())
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        return run(sys.argv[1:] if arguments is None else arguments)
    except (AndroidAutomationError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
