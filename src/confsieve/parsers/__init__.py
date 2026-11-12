"""Configuration file parsers for YAML, JSON, and TOML."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from ..core import ConfigKey
from .yaml_parser import YamlParser
from .json_parser import JsonParser
from .toml_parser import TomlParser


def parse_config_file(file_path: Path) -> List[ConfigKey]:
    """Parse a configuration file based on its extension."""
    suffix = file_path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return YamlParser.parse_file(file_path)
    elif suffix == ".json":
        return JsonParser.parse_file(file_path)
    elif suffix == ".toml":
        return TomlParser.parse_file(file_path)
    return []


def parse_config_paths(paths: List[Path]) -> Tuple[List[ConfigKey], List[str]]:
    """Parse multiple configuration files or directories."""
    all_keys: List[ConfigKey] = []
    scanned_files: List[str] = []

    for p in paths:
        if p.is_file():
            keys = parse_config_file(p)
            if keys:
                all_keys.extend(keys)
                scanned_files.append(str(p))
        elif p.is_dir():
            for child in p.rglob("*"):
                if child.is_file() and child.suffix.lower() in (".yaml", ".yml", ".json", ".toml"):
                    if any(part.startswith(".") for part in child.parts):
                        continue
                    keys = parse_config_file(child)
                    if keys:
                        all_keys.extend(keys)
                        scanned_files.append(str(child))

    return all_keys, scanned_files


__all__ = [
    "YamlParser",
    "JsonParser",
    "TomlParser",
    "parse_config_file",
    "parse_config_paths",
]
