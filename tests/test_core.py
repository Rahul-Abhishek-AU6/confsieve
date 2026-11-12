"""Unit tests for ConfSieve drift analysis engine."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.core import ConfSieve, ConfigKey, CodeLookup


class TestConfSieveCore(unittest.TestCase):
    def test_ghost_detection(self) -> None:
        manifest_keys = [
            ConfigKey(path="db.host", parts=("db", "host"), file_path="config.yaml", line_number=2),
        ]
        code_lookups = [
            CodeLookup(
                path="db.host",
                parts=("db", "host"),
                file_path="app.py",
                line_number=10,
                access_type="subscript",
                object_name="config",
            ),
            CodeLookup(
                path="stripe.secret_key",
                parts=("stripe", "secret_key"),
                file_path="app.py",
                line_number=20,
                access_type="subscript",
                object_name="config",
            ),
        ]

        sieve = ConfSieve()
        report = sieve.analyze(
            code_lookups=code_lookups,
            manifest_keys=manifest_keys,
            code_files=["app.py"],
            config_files=["config.yaml"],
        )

        self.assertTrue(report.has_drift)
        self.assertEqual(len(report.ghost_keys), 1)
        self.assertEqual(report.ghost_keys[0].path, "stripe.secret_key")
        self.assertEqual(len(report.zombie_keys), 0)
        self.assertEqual(report.matched_keys, ["db.host"])

    def test_zombie_detection(self) -> None:
        manifest_keys = [
            ConfigKey(path="server.port", parts=("server", "port"), file_path="config.yaml", line_number=2),
            ConfigKey(path="legacy_flag", parts=("legacy_flag",), file_path="config.yaml", line_number=5),
        ]
        code_lookups = [
            CodeLookup(
                path="server.port",
                parts=("server", "port"),
                file_path="main.py",
                line_number=5,
                access_type="get",
                object_name="config",
            ),
        ]

        sieve = ConfSieve()
        report = sieve.analyze(
            code_lookups=code_lookups,
            manifest_keys=manifest_keys,
            code_files=["main.py"],
            config_files=["config.yaml"],
        )

        self.assertTrue(report.has_drift)
        self.assertEqual(len(report.ghost_keys), 0)
        self.assertEqual(len(report.zombie_keys), 1)
        self.assertEqual(report.zombie_keys[0].path, "legacy_flag")

    def test_clean_parity(self) -> None:
        manifest_keys = [
            ConfigKey(path="api_key", parts=("api_key",), file_path="config.yaml", line_number=1),
        ]
        code_lookups = [
            CodeLookup(
                path="api_key",
                parts=("api_key",),
                file_path="client.py",
                line_number=3,
                access_type="subscript",
                object_name="config",
            ),
        ]

        sieve = ConfSieve()
        report = sieve.analyze(
            code_lookups=code_lookups,
            manifest_keys=manifest_keys,
            code_files=["client.py"],
            config_files=["config.yaml"],
        )

        self.assertFalse(report.has_drift)
        self.assertEqual(len(report.ghost_keys), 0)
        self.assertEqual(len(report.zombie_keys), 0)
        self.assertEqual(report.matched_keys, ["api_key"])

    def test_ignore_keys(self) -> None:
        manifest_keys = [
            ConfigKey(path="ignored_zombie", parts=("ignored_zombie",), file_path="config.yaml", line_number=1),
        ]
        code_lookups = [
            CodeLookup(
                path="ignored_ghost",
                parts=("ignored_ghost",),
                file_path="client.py",
                line_number=3,
                access_type="get",
                object_name="config",
            ),
        ]

        sieve = ConfSieve(ignore_keys={"ignored_zombie", "ignored_ghost"})
        report = sieve.analyze(
            code_lookups=code_lookups,
            manifest_keys=manifest_keys,
            code_files=["client.py"],
            config_files=["config.yaml"],
        )

        self.assertFalse(report.has_drift)
        self.assertEqual(len(report.ghost_keys), 0)
        self.assertEqual(len(report.zombie_keys), 0)
        self.assertIn("ignored_zombie", report.ignored_keys)
        self.assertIn("ignored_ghost", report.ignored_keys)


if __name__ == "__main__":
    unittest.main()
