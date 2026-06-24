from pathlib import Path
import os
import tempfile
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

    def test_load_dotenv_reads_values_without_overriding_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                'TEST_EXISTING="from-file"\nTEST_NEW=from-file\n',
                encoding="utf-8",
            )
            os.environ["TEST_EXISTING"] = "from-environment"
            os.environ.pop("TEST_NEW", None)
            try:
                run.load_dotenv(path)
                self.assertEqual(os.environ["TEST_EXISTING"], "from-environment")
                self.assertEqual(os.environ["TEST_NEW"], "from-file")
            finally:
                os.environ.pop("TEST_EXISTING", None)
                os.environ.pop("TEST_NEW", None)


if __name__ == "__main__":
    unittest.main()
