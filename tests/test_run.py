from pathlib import Path
import unittest

import run


class BootstrapTests(unittest.TestCase):
    def test_fingerprint_is_stable_sha256(self) -> None:
        fingerprint = run.installation_fingerprint()
        self.assertEqual(len(fingerprint), 64)
        int(fingerprint, 16)

    def test_virtual_environment_python_is_platform_appropriate(self) -> None:
        path = run.venv_python()
        self.assertIsInstance(path, Path)
        self.assertIn(".venv", str(path))


if __name__ == "__main__":
    unittest.main()
