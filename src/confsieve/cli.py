"""Command-line interface for ConfSieve."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .core import ConfSieve
from .extractors.python_extractor import PythonExtractor, DEFAULT_CONFIG_OBJECTS
from .parsers import parse_config_paths
from .reporter import print_terminal_summary, print_json_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="confsieve",
        description="ConfSieve: Zero-dependency configuration key drift detector.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"confsieve {__version__}",
    )
    parser.add_argument(
        "--code",
        "-c",
        nargs="+",
        default=["."],
        help="Path(s) to Python code files or directories to scan (default: current directory).",
    )
    parser.add_argument(
        "--config",
        "-f",
        nargs="+",
        required=True,
        help="Path(s) to configuration manifest files (.yaml, .json, .toml) or directory.",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        action="append",
        default=[],
        help="Configuration key path(s) to ignore (can be passed multiple times).",
    )
    parser.add_argument(
        "--target-object",
        action="append",
        default=[],
        help="Additional configuration object names to detect (e.g. 'app.settings').",
    )
    parser.add_argument(
        "--no-fail-on-zombie",
        action="store_true",
        help="Do not return exit code 1 if zombie keys are found (report as warnings).",
    )
    parser.add_argument(
        "--no-fail-on-ghost",
        action="store_true",
        help="Do not return exit code 1 if ghost keys are found.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON format instead of terminal text.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in terminal output.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    code_paths = [Path(p).resolve() for p in args.code]
    config_paths = [Path(p).resolve() for p in args.config]

    # Validate config paths exist
    for cp in config_paths:
        if not cp.exists():
            sys.stderr.write(f"Error: Configuration path does not exist: {cp}\n")
            return 2

    # Configure targets
    targets = set(DEFAULT_CONFIG_OBJECTS)
    if args.target_object:
        targets.update(args.target_object)

    # Extract code lookups
    extractor = PythonExtractor(target_objects=targets)
    code_lookups, scanned_code_files = extractor.extract_from_paths(code_paths)

    # Parse config keys
    manifest_keys, scanned_config_files = parse_config_paths(config_paths)

    # Run drift analysis
    sieve = ConfSieve(
        ignore_keys=set(args.ignore),
        check_zombies=True,
        check_ghosts=True,
    )
    report = sieve.analyze(
        code_lookups=code_lookups,
        manifest_keys=manifest_keys,
        code_files=scanned_code_files,
        config_files=scanned_config_files,
    )

    # Render results
    if args.json:
        print_json_report(report)
    else:
        print_terminal_summary(
            report,
            use_color=not args.no_color and sys.stdout.isatty(),
        )

    # Determine exit code
    has_ghost_failure = bool(report.ghost_keys) and not args.no_fail_on_ghost
    has_zombie_failure = bool(report.zombie_keys) and not args.no_fail_on_zombie

    if has_ghost_failure or has_zombie_failure:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
