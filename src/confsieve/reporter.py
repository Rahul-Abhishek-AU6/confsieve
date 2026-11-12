"""Terminal formatting and machine-readable output for ConfSieve."""
from __future__ import annotations

import json
import sys
from typing import Optional, TextIO

from .core import DriftReport


# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GRAY = "\033[90m"


def print_terminal_summary(
    report: DriftReport,
    stream: Optional[TextIO] = None,
    use_color: bool = True,
) -> None:
    """Render a human-readable terminal receipt with ANSI colors."""
    if stream is None:
        stream = sys.stdout

    def c(code: str, text: str) -> str:
        return f"{code}{text}{RESET}" if use_color else text

    stream.write(f"\n{c(BOLD + CYAN, '═' * 68)}\n")
    stream.write(f"{c(BOLD + CYAN, '  ConfSieve: Configuration Drift Receipt')}\n")
    stream.write(f"{c(BOLD + CYAN, '═' * 68)}\n\n")

    # Scanned files metadata
    stream.write(f"{c(BOLD, 'Scanned Files:')}\n")
    stream.write(f"  Code Files   ({len(report.scanned_code_files)}): {', '.join(report.scanned_code_files) or 'None'}\n")
    stream.write(f"  Config Files ({len(report.scanned_config_files)}): {', '.join(report.scanned_config_files) or 'None'}\n")
    if report.ignored_keys:
        stream.write(f"  Ignored Keys ({len(report.ignored_keys)}): {', '.join(report.ignored_keys)}\n")
    stream.write("\n")

    # Section 1: Ghost Keys (In Code, Missing in Config)
    if report.ghost_keys:
        stream.write(f"{c(BOLD + RED, '👻 GHOST CONFIGURATIONS')} {c(RED, f'({len(report.ghost_keys)} detected)')}\n")
        stream.write(f"{c(GRAY, '   Code accesses these keys, but they do NOT exist in the configuration manifest:')}\n\n")
        for ghost in report.ghost_keys:
            default_str = f" {c(GRAY, f'(default: {ghost.default_value})')}" if ghost.default_value else ""
            stream.write(
                f"  {c(RED, '✖')} {c(BOLD, ghost.path)}{default_str}\n"
                f"    {c(GRAY, 'at')} {ghost.file_path}:{ghost.line_number} "
                f"{c(GRAY, f'[{ghost.object_name} via {ghost.access_type}]')}\n"
            )
        stream.write("\n")
    else:
        stream.write(f"{c(GREEN, '✔ No Ghost configurations detected. All code lookups exist in manifest.')}\n\n")

    # Section 2: Zombie Keys (In Config, Dead in Code)
    if report.zombie_keys:
        stream.write(f"{c(BOLD + YELLOW, '🧟 ZOMBIE CONFIGURATIONS')} {c(YELLOW, f'({len(report.zombie_keys)} detected)')}\n")
        stream.write(f"{c(GRAY, '   Declared in configuration manifest, but NEVER accessed anywhere in code:')}\n\n")
        for zombie in report.zombie_keys:
            stream.write(
                f"  {c(YELLOW, '⚠')} {c(BOLD, zombie.path)}\n"
                f"    {c(GRAY, 'at')} {zombie.file_path}:{zombie.line_number} "
                f"{c(GRAY, f'[{zombie.manifest_type}]')}\n"
            )
        stream.write("\n")
    else:
        stream.write(f"{c(GREEN, '✔ No Zombie configurations detected. All manifest keys are utilized.')}\n\n")

    # Section 3: Summary Box
    status_label = c(BOLD + RED, 'FAIL: DRIFT DETECTED') if report.has_drift else c(BOLD + GREEN, 'PASS: CLEAN PARITY')
    stream.write(f"{c(BOLD, 'Summary:')}\n")
    stream.write(f"  Status        : {status_label}\n")
    stream.write(f"  Code Lookups  : {report.total_code_lookups}\n")
    stream.write(f"  Manifest Keys : {report.total_manifest_keys}\n")
    stream.write(f"  Matched Keys  : {len(report.matched_keys)}\n")
    stream.write(f"  Ghost Keys    : {len(report.ghost_keys)}\n")
    stream.write(f"  Zombie Keys   : {len(report.zombie_keys)}\n")
    stream.write(f"{c(BOLD + CYAN, '═' * 68)}\n\n")


def print_json_report(report: DriftReport, stream: Optional[TextIO] = None) -> None:
    """Output machine-readable JSON for CI integration."""
    if stream is None:
        stream = sys.stdout
    stream.write(json.dumps(report.to_dict(), indent=2) + "\n")
