# Android Automation

A focused, app-agnostic toolkit for inspecting and controlling Android devices
through ADB.

The project provides:

- device discovery and selection
- app launch and data reset
- screenshots and UI hierarchy dumps
- searchable Android UI nodes
- taps, text input, key events, and explicit shell commands
- optional goal-driven UI automation with Gemini

The original application-specific onboarding, account generation, mocked-trip
service, hard-coded user data, and generated logs have been removed. Figma
comparison is intentionally disabled and is not part of the current runtime.

## Requirements

- Python 3.10+
- Android platform tools (`adb`) available on `PATH`
- an Android device or emulator with USB debugging enabled

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

For optional AI-driven automation:

```bash
python -m pip install -e ".[agent]"
export GEMINI_API_KEY="your-key"
```

## Use

Running the tool without arguments shows the deliberately minimal command list:

```bash
android-automation
```

Common commands:

```bash
android-automation devices
android-automation --device emulator-5554 launch com.example.app
android-automation screenshot artifacts/home.png
android-automation dump-ui --clickable
android-automation find --text "Continue"
android-automation tap 540 1200
android-automation input "hello world"
android-automation key BACK
android-automation agent "Open settings and enable notifications"
```

Set `ANDROID_AUTOMATION_DEVICE` to avoid passing `--device` repeatedly.

## Architecture

- `adb.py` owns process execution and device operations.
- `ui.py` parses UIAutomator XML into typed, searchable objects.
- `agent.py` translates model responses into a small allowlisted action set.
- `cli.py` is the thin user interface and dependency wiring layer.

Core device and UI functionality has no third-party Python dependency. The
Gemini integration is lazy-loaded only when the `agent` command is used.

## Safety

AI-generated actions are restricted to tap, text input, key events, waiting,
and completion. Models cannot emit arbitrary shell commands. The `shell`
subcommand remains available for commands explicitly entered by the operator.

## Development

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests
```
