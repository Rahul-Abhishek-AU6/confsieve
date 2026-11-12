"""Unit tests for AST Python configuration extractors."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.extractors.python_extractor import PythonExtractor


class TestPythonExtractor(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PythonExtractor()

    def test_subscript_extraction(self) -> None:
        code = """
def init_app(config):
    port = config["server"]["port"]
    host = config["host"]
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            lookups = self.extractor.extract_from_file(temp_path)
            paths = {l.path for l in lookups}
            self.assertIn("server.port", paths)
            self.assertIn("host", paths)
            self.assertEqual(len(lookups), 2)
        finally:
            temp_path.unlink()

    def test_get_call_with_default(self) -> None:
        code = """
def run(cfg):
    timeout = cfg.get("timeout_seconds", 30)
    flag = cfg.get("features.v2", False)
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            lookups = self.extractor.extract_from_file(temp_path)
            timeout_lookup = next(l for l in lookups if l.path == "timeout_seconds")
            self.assertEqual(timeout_lookup.default_value, "30")

            v2_lookup = next(l for l in lookups if l.path == "features.v2")
            self.assertEqual(v2_lookup.default_value, "False")
        finally:
            temp_path.unlink()

    def test_attribute_access(self) -> None:
        code = """
import settings

def connect():
    url = settings.DATABASE_URL
    debug = settings.DEBUG
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            lookups = self.extractor.extract_from_file(temp_path)
            paths = {l.path for l in lookups}
            self.assertIn("DATABASE_URL", paths)
            self.assertIn("DEBUG", paths)
        finally:
            temp_path.unlink()

    def test_syntax_error_resilience(self) -> None:
        code = "def broken(: syntax error"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            lookups = self.extractor.extract_from_file(temp_path)
            self.assertEqual(lookups, [])
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
