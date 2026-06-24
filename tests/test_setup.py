from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import setup


class SetupTests(unittest.TestCase):
    def test_fingerprint_is_stable_sha256(self) -> None:
        fingerprint = setup.installation_fingerprint()
        self.assertEqual(len(fingerprint), 64)
        int(fingerprint, 16)

    def test_virtual_environment_python_is_platform_appropriate(self) -> None:
        path = setup.venv_python()
        self.assertIsInstance(path, Path)
        self.assertIn(".venv", str(path))

    def test_packaging_commands_are_separated_from_user_setup(self) -> None:
        self.assertTrue(setup.is_packaging_invocation(["egg_info"]))
        self.assertTrue(setup.is_packaging_invocation(["editable_wheel"]))
        self.assertFalse(setup.is_packaging_invocation([]))
        self.assertFalse(setup.is_packaging_invocation(["--force"]))

    @patch("setup.runtime_is_ready", return_value=True)
    @patch("setup.install")
    def test_ensure_runtime_skips_install_when_ready(self, install, ready) -> None:
        self.assertEqual(setup.ensure_runtime(), setup.venv_python())
        install.assert_not_called()

    @patch("setup.runtime_is_ready", return_value=False)
    @patch("setup.install")
    def test_ensure_runtime_installs_when_missing(self, install, ready) -> None:
        expected = Path("/tmp/python")
        install.return_value = expected
        self.assertEqual(setup.ensure_runtime(), expected)
        install.assert_called_once_with(force=False)


if __name__ == "__main__":
    unittest.main()
