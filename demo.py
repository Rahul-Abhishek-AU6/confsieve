#!/usr/bin/env python3
"""Interactive demonstration of ConfSieve detecting configuration drift."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.core import ConfSieve
from confsieve.extractors.python_extractor import PythonExtractor
from confsieve.parsers import parse_config_paths
from confsieve.reporter import print_terminal_summary


SAMPLE_CODE = '''# billing_service.py
from typing import Dict, Any

def process_payment(order_id: str, config: Dict[str, Any]) -> bool:
    # Matched keys:
    db_host = config["database"]["host"]
    db_port = config["database"]["port"]
    log_level = config.get("log_level", "INFO")
    
    # GHOST KEY: Added in recent feature refactor, but missing from config.yaml!
    timeout = config.get("payment_gateway_timeout", 30)
    stripe_key = config["stripe_webhook_secret"]
    
    print(f"Connecting to {db_host}:{db_port} with timeout {timeout}s...")
    return True
'''

SAMPLE_YAML = '''# config.yaml - Application configuration manifest
log_level: "DEBUG"

database:
  host: "db.internal.net"
  port: 5432
  pool_size: 20

# ZOMBIE KEY: Leftover from legacy v1 auth system, no longer read by code!
legacy_auth_token: "tok_test_legacy_12345"
legacy_sso_endpoint: "https://sso-v1.internal.net"
'''


def run_demo() -> int:
    print("=" * 68)
    print("  ConfSieve Live Demonstration: Detecting Configuration Drift")
    print("=" * 68)
    print("\nScenario: An engineer adds a payment timeout & webhook secret to code,")
    print("but forgets to add them to config.yaml. Meanwhile, legacy auth keys remain in config.yaml.")
    print("-" * 68)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_file = tmp_path / "billing_service.py"
        config_file = tmp_path / "config.yaml"

        code_file.write_text(SAMPLE_CODE, encoding="utf-8")
        config_file.write_text(SAMPLE_YAML, encoding="utf-8")

        print(f"\n[1] Scanning Python code ({code_file.name})...")
        extractor = PythonExtractor()
        code_lookups, code_files = extractor.extract_from_paths([code_file])
        print(f"    Found {len(code_lookups)} configuration lookups across {len(code_files)} file.")

        print(f"\n[2] Parsing configuration manifest ({config_file.name})...")
        manifest_keys, config_files_list = parse_config_paths([config_file])
        print(f"    Found {len(manifest_keys)} keys across {len(config_files_list)} manifest.")

        print("\n[3] Running ConfSieve drift analysis...")
        sieve = ConfSieve()
        report = sieve.analyze(
            code_lookups=code_lookups,
            manifest_keys=manifest_keys,
            code_files=code_files,
            config_files=config_files_list,
        )

        print("\n[4] Rendering Terminal Receipt:")
        print_terminal_summary(report, use_color=sys.stdout.isatty())

        print("Demonstration completed successfully.")
        return 0 if report.has_drift else 1


if __name__ == "__main__":
    sys.exit(run_demo())
