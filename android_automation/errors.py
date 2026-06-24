class AndroidAutomationError(Exception):
    """Base exception for expected automation failures."""


class AdbNotFoundError(AndroidAutomationError):
    """ADB is not installed or is not available on PATH."""


class AdbCommandError(AndroidAutomationError):
    """An ADB command returned a non-zero exit code."""


class DeviceSelectionError(AndroidAutomationError):
    """A usable Android device could not be selected."""


class AgentConfigurationError(AndroidAutomationError):
    """The optional agent is missing configuration or dependencies."""
