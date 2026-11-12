#!/usr/bin/env python3
"""Launcher for ConfSieve from project root."""
import sys
from pathlib import Path

# Add src to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from confsieve.cli import main

if __name__ == "__main__":
    sys.exit(main())
