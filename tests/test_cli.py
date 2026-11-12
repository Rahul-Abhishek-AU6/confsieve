"""Integration tests for the ConfSieve CLI."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.cli import main


class TestCli(unittest.TestCase):
    def test_cli_clean_parity_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            code = tmp_path / "app.py"
            conf = tmp_path / "config.json"

            code.write_text('def run(config): return config["port"]\n', encoding="utf-8")
            conf.write_text('{"port": 8080}\n', encoding="utf-8")

            exit_code = main(["--code", str(code), "--config", str(conf)])
            self.assertEqual(exit_code, 0)

    def test_cli_drift_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            code = tmp_path / "app.py"
            conf = tmp_path / "config.json"

            code.write_text('def run(config): return config["ghost_key"]\n', encoding="utf-8")
            conf.write_text('{"port": 8080}\n', encoding="utf-8")

            exit_code = main(["--code", str(code), "--config", str(conf)])
            self.assertEqual(exit_code, 1)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            code = tmp_path / "app.py"
            conf = tmp_path / "config.json"

            code.write_text('def run(config): return config["ghost_key"]\n', encoding="utf-8")
            conf.write_text('{"port": 8080}\n', encoding="utf-8")

            # Capture stdout
            captured = io.StringIO()
            with redirect_stdout(captured):
                exit_code = main(["--code", str(code), "--config", str(conf), "--json"])

            self.assertEqual(exit_code, 1)
            output = captured.getvalue()
            parsed = json.loads(output)
            self.assertTrue(parsed["summary"]["has_drift"])
            self.assertEqual(parsed["summary"]["ghost_count"], 1)
            self.assertEqual(parsed["summary"]["zombie_count"], 1)

    def test_cli_missing_config_exit_2(self) -> None:
        exit_code = main(["--code", ".", "--config", "nonexistent_file_12345.yaml"])
        self.assertEqual(exit_code, 2)

    def test_cli_no_fail_on_zombie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            code = tmp_path / "app.py"
            conf = tmp_path / "config.json"

            # Code matches port, but config also has legacy zombie
            code.write_text('def run(config): return config["port"]\n', encoding="utf-8")
            conf.write_text('{"port": 8080, "legacy_key": 1}\n', encoding="utf-8")

            exit_code = main(["--code", str(code), "--config", str(conf), "--no-fail-on-zombie"])
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
