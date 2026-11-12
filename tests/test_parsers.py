"""Unit tests for configuration manifest parsers."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.parsers.yaml_parser import YamlParser
from confsieve.parsers.json_parser import JsonParser
from confsieve.parsers.toml_parser import TomlParser
from confsieve.parsers import parse_config_paths, parse_config_file


class TestYamlParser(unittest.TestCase):
    def test_nested_yaml_parsing(self) -> None:
        content = """# App Config
app:
  name: "demo"
  version: "1.0.0"

database:
  host: "localhost"
  port: 5432
  credentials:
    username: "admin"
"""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            keys = YamlParser.parse_file(temp_path)
            paths = {k.path for k in keys}
            self.assertIn("app", paths)
            self.assertIn("app.name", paths)
            self.assertIn("database.host", paths)
            self.assertIn("database.credentials.username", paths)

            # Check line numbers
            db_port_key = next(k for k in keys if k.path == "database.port")
            self.assertEqual(db_port_key.line_number, 8)
        finally:
            temp_path.unlink()

    def test_empty_or_comment_yaml(self) -> None:
        content = "# Just comments\n\n# nothing here\n"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            keys = YamlParser.parse_file(temp_path)
            self.assertEqual(len(keys), 0)
        finally:
            temp_path.unlink()


class TestJsonParser(unittest.TestCase):
    def test_json_parsing(self) -> None:
        content = """{
  "server": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "debug": true
}"""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            keys = JsonParser.parse_file(temp_path)
            paths = {k.path for k in keys}
            self.assertIn("server", paths)
            self.assertIn("server.host", paths)
            self.assertIn("server.port", paths)
            self.assertIn("debug", paths)
        finally:
            temp_path.unlink()


class TestTomlParser(unittest.TestCase):
    def test_toml_parsing(self) -> None:
        content = """[server]
host = "127.0.0.1"
port = 9000

[database]
name = "production"
"""
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            keys = TomlParser.parse_file(temp_path)
            paths = {k.path for k in keys}
            self.assertIn("server.host", paths)
            self.assertIn("server.port", paths)
            self.assertIn("database.name", paths)
        finally:
            temp_path.unlink()


class TestParseConfigPaths(unittest.TestCase):
    def test_multi_path_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            (dir_path / "app.json").write_text('{"api_key": "123"}', encoding="utf-8")
            (dir_path / "db.yaml").write_text("port: 5432\n", encoding="utf-8")

            keys, files = parse_config_paths([dir_path])
            paths = {k.path for k in keys}
            self.assertIn("api_key", paths)
            self.assertIn("port", paths)
            self.assertEqual(len(files), 2)


if __name__ == "__main__":
    unittest.main()
