from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run


class RunTests(unittest.TestCase):
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

    @patch("run.execute")
    @patch("run.project_setup.ensure_runtime")
    @patch("run.project_setup.runtime_is_ready", return_value=True)
    def test_healthy_runtime_runs_without_setup(
        self, ready, ensure_runtime, execute
    ) -> None:
        execute.return_value = subprocess.CompletedProcess([], 0)
        self.assertEqual(run.main(["providers"]), 0)
        ensure_runtime.assert_not_called()
        execute.assert_called_once_with(["providers"])

    @patch("run.execute")
    @patch("run.project_setup.ensure_runtime")
    @patch("run.project_setup.runtime_is_ready", return_value=False)
    def test_missing_runtime_runs_setup_then_command(
        self, ready, ensure_runtime, execute
    ) -> None:
        execute.return_value = subprocess.CompletedProcess([], 0)
        self.assertEqual(run.main(["providers"]), 0)
        ensure_runtime.assert_called_once_with()
        execute.assert_called_once_with(["providers"])

    @patch("run.execute")
    @patch("run.project_setup.ensure_runtime")
    @patch("run.project_setup.runtime_is_ready", return_value=True)
    def test_start_failure_repairs_once_and_retries(
        self, ready, ensure_runtime, execute
    ) -> None:
        execute.side_effect = [
            subprocess.CompletedProcess([], 127),
            subprocess.CompletedProcess([], 0),
        ]
        self.assertEqual(run.main(["providers"]), 0)
        ensure_runtime.assert_called_once_with(force=True)
        self.assertEqual(execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
