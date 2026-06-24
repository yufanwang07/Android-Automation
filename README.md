# Android Automation

A small, app-agnostic toolkit for inspecting and controlling Android devices
through ADB, with optional goal-driven automation.

## One-command setup

Requirements:

- Python 3.10 or newer
- Android platform tools (`adb`) on `PATH`
- an Android device or emulator with USB debugging enabled

Run:

```bash
python run.py
```

`run.py` creates `.venv`, installs the project and all supported AI provider
SDKs, and starts the minimal CLI. It is safe to run again; dependencies are
reinstalled only when `pyproject.toml` changes.

Useful first checks:

```bash
python run.py doctor
python run.py devices
```

The launcher works on macOS, Linux, and Windows. If the Python used to start it
is too old, it searches for an installed `python3.10` or newer before stopping
with an installation link.

## AI providers

The agent supports three native provider APIs:

| Provider | API | Default model | API key |
| --- | --- | --- | --- |
| Gemini | Interactions API | `gemini-3.5-flash` | `GEMINI_API_KEY` |
| OpenAI | Responses API | `gpt-5.4-mini` | `OPENAI_API_KEY` |
| Anthropic | Messages API | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |

Each integration uses the provider's native structured-output feature. This is
intentional: Anthropic documents that its OpenAI compatibility layer does not
guarantee strict schema conformance.

Set an API key, then choose a provider directly:

```bash
export OPENAI_API_KEY="your-key"
python run.py agent "Open settings" --provider openai
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-key"
python run.py agent "Open settings" --provider openai
```

Provider and model selection can come from, in increasing precedence:

1. the default config file
2. a project `.android-automation.json`
3. `ANDROID_AUTOMATION_*` environment variables
4. command-line flags

Create and inspect the user config:

```bash
python run.py config init --provider anthropic
python run.py config show
python run.py providers
```

Use a specific config file:

```bash
python run.py --config ./team-config.json agent "Complete the current form"
```

Supported environment overrides:

```text
ANDROID_AUTOMATION_CONFIG
ANDROID_AUTOMATION_PROVIDER
ANDROID_AUTOMATION_MODEL
ANDROID_AUTOMATION_MAX_STEPS
ANDROID_AUTOMATION_STEP_DELAY
ANDROID_AUTOMATION_MAX_OUTPUT_TOKENS
ANDROID_AUTOMATION_BASE_URL
ANDROID_AUTOMATION_DEVICE
```

API keys are read from provider-standard environment variables and are never
written to the config file.

## Device commands

```bash
python run.py devices
python run.py --device emulator-5554 launch com.example.app
python run.py screenshot artifacts/home.png
python run.py dump-ui --clickable
python run.py find --text "Continue"
python run.py tap 540 1200
python run.py input "hello world"
python run.py key BACK
```

## Architecture

- `adb.py` owns process execution and device operations.
- `ui.py` parses UIAutomator XML into typed, searchable objects.
- `config.py` resolves file, environment, and CLI configuration.
- `providers.py` contains native Gemini, OpenAI, and Anthropic adapters.
- `agent.py` executes a small allowlisted action protocol.
- `cli.py` is the presentation and dependency-wiring layer.
- `run.py` is the dependency-free bootstrap and launch path.

AI-generated actions are restricted to tap, text input, key events, waiting,
success, and stop. Models cannot emit arbitrary shell commands. The `shell`
subcommand remains available only for commands explicitly entered by the
operator.

Application-specific onboarding, account generation, trip mocking, hard-coded
personal data, generated logs, and Figma comparison are not part of this
project.

## Manual installation

Install everything:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[all]"
```

Install only one provider:

```bash
python -m pip install -e ".[gemini]"
python -m pip install -e ".[openai]"
python -m pip install -e ".[anthropic]"
```

## Development

```bash
python -m unittest discover -s tests -v
```

The provider request shapes follow the current official documentation:

- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
