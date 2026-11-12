"""ConfSieve: Zero-dependency configuration key drift detector.

Finds ghost configuration lookups in source code and zombie keys in YAML/JSON/TOML manifests.
"""

__version__ = "0.1.0"
__author__ = "ConfSieve Authors"

from .core import ConfSieve, DriftReport, ConfigKey, CodeLookup

__all__ = ["ConfSieve", "DriftReport", "ConfigKey", "CodeLookup", "__version__"]
