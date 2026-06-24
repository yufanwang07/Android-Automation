from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .adb import AdbClient
from .agent import GeminiProvider, UiAgent
from .errors import AndroidAutomationError
from .ui import UiHierarchy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="android-automation",
        description="Minimal Android automation through ADB.",
    )
    parser.add_argument("--device", help="ADB device serial")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("devices", help="List connected devices")

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
    agent.add_argument("--model")
    agent.add_argument("--max-steps", type=int, default=20)

    return parser


def print_landing(parser: argparse.ArgumentParser) -> None:
    print("Android Automation")
    print()
    print("  devices            list connected devices")
    print("  launch PACKAGE     launch an app")
    print("  screenshot FILE    save the current screen")
    print("  dump-ui            inspect the current UI")
    print("  agent GOAL         run goal-driven automation")
    print()
    print(f"Run '{parser.prog} --help' for all commands.")


def _print_nodes(hierarchy: UiHierarchy, *, clickables: bool = False) -> None:
    nodes = hierarchy.clickables() if clickables else hierarchy.visible()
    if not nodes:
        print("No matching UI nodes.")
        return
    for node in nodes:
        print(node.summary())


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
        provider = GeminiProvider.from_environment(args.model)
        result = UiAgent(client, provider, max_steps=args.max_steps).run(args.goal)
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
