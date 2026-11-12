"""Core models and drift analysis engine for ConfSieve."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set, List, Dict, Any, Tuple


@dataclass(frozen=True)
class ConfigKey:
    """A configuration key declared in a configuration manifest file."""
    path: str
    parts: Tuple[str, ...]
    file_path: str
    line_number: int
    manifest_type: str = "yaml"

    @property
    def top_level(self) -> str:
        return self.parts[0] if self.parts else self.path


@dataclass(frozen=True)
class CodeLookup:
    """A configuration access identified in source code."""
    path: str
    parts: Tuple[str, ...]
    file_path: str
    line_number: int
    access_type: str  # 'subscript', 'get', 'attr'
    object_name: str  # 'config', 'settings', etc.
    default_value: Optional[str] = None

    @property
    def top_level(self) -> str:
        return self.parts[0] if self.parts else self.path


@dataclass
class DriftReport:
    """Summary and detail report of configuration drift."""
    ghost_keys: List[CodeLookup] = field(default_factory=list)
    zombie_keys: List[ConfigKey] = field(default_factory=list)
    matched_keys: List[str] = field(default_factory=list)
    total_code_lookups: int = 0
    total_manifest_keys: int = 0
    scanned_code_files: List[str] = field(default_factory=list)
    scanned_config_files: List[str] = field(default_factory=list)
    ignored_keys: List[str] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.ghost_keys or self.zombie_keys)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "has_drift": self.has_drift,
                "ghost_count": len(self.ghost_keys),
                "zombie_count": len(self.zombie_keys),
                "matched_count": len(self.matched_keys),
                "total_code_lookups": self.total_code_lookups,
                "total_manifest_keys": self.total_manifest_keys,
            },
            "ghost_keys": [
                {
                    "path": k.path,
                    "parts": list(k.parts),
                    "file": k.file_path,
                    "line": k.line_number,
                    "access_type": k.access_type,
                    "object": k.object_name,
                    "default": k.default_value,
                }
                for k in self.ghost_keys
            ],
            "zombie_keys": [
                {
                    "path": k.path,
                    "parts": list(k.parts),
                    "file": k.file_path,
                    "line": k.line_number,
                    "manifest_type": k.manifest_type,
                }
                for k in self.zombie_keys
            ],
            "scanned_code_files": self.scanned_code_files,
            "scanned_config_files": self.scanned_config_files,
            "ignored_keys": self.ignored_keys,
        }


class ConfSieve:
    """Engine that compares code lookups against configuration keys."""

    def __init__(
        self,
        ignore_keys: Optional[Set[str]] = None,
        check_zombies: bool = True,
        check_ghosts: bool = True,
    ) -> None:
        self.ignore_keys = set(ignore_keys or [])
        self.check_zombies = check_zombies
        self.check_ghosts = check_ghosts

    def analyze(
        self,
        code_lookups: List[CodeLookup],
        manifest_keys: List[ConfigKey],
        code_files: List[str],
        config_files: List[str],
    ) -> DriftReport:
        """Analyze code lookups and manifest keys to detect drift."""
        # Build lookup indices
        manifest_path_map: Dict[str, ConfigKey] = {}
        manifest_top_levels: Set[str] = set()

        for mk in manifest_keys:
            manifest_path_map[mk.path] = mk
            manifest_top_levels.add(mk.top_level)

        code_paths_used: Set[str] = set()
        code_top_levels_used: Set[str] = set()

        ghost_keys: List[CodeLookup] = []
        ignored_list: List[str] = []

        # Find ghosts: code lookups not present in manifest
        for lookup in code_lookups:
            if lookup.path in self.ignore_keys or lookup.top_level in self.ignore_keys:
                ignored_list.append(lookup.path)
                continue

            code_paths_used.add(lookup.path)
            code_top_levels_used.add(lookup.top_level)

            if not self.check_ghosts:
                continue

            # A lookup is matched if:
            # 1. Exact path matches: 'database.port' in manifest
            # 2. Top-level object matches: code does config['database'], manifest has database.port
            # 3. Path matches a prefix of a nested structure
            is_matched = (
                lookup.path in manifest_path_map
                or lookup.top_level in manifest_top_levels
            )

            if not is_matched:
                ghost_keys.append(lookup)

        # Find zombies: manifest keys not referenced in code
        zombie_keys: List[ConfigKey] = []
        matched_keys: List[str] = []

        for mk in manifest_keys:
            if mk.path in self.ignore_keys or mk.top_level in self.ignore_keys:
                ignored_list.append(mk.path)
                continue

            # A manifest key is matched if:
            # 1. Exactly referenced: 'database.port' in code_paths_used
            # 2. Top-level referenced: 'database' was accessed as a dict/object
            is_matched = (
                mk.path in code_paths_used
                or mk.top_level in code_top_levels_used
            )

            if is_matched:
                matched_keys.append(mk.path)
            elif self.check_zombies:
                zombie_keys.append(mk)

        return DriftReport(
            ghost_keys=ghost_keys,
            zombie_keys=zombie_keys,
            matched_keys=sorted(list(set(matched_keys))),
            total_code_lookups=len(code_lookups),
            total_manifest_keys=len(manifest_keys),
            scanned_code_files=sorted(code_files),
            scanned_config_files=sorted(config_files),
            ignored_keys=sorted(list(set(ignored_list))),
        )
