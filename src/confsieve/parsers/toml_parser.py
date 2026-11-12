"""TOML configuration parser with section and key path tracking."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..core import ConfigKey

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


class TomlParser:
    """Parses TOML configuration files."""

    SECTION_REGEX = re.compile(r"^\s*\[([A-Za-z0-9_\.\-]+)\]\s*$")
    KEY_REGEX = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*=(?:\s*(.*))?$")

    @classmethod
    def _traverse_dict(
        cls,
        data: Dict[str, Any],
        parent_parts: Tuple[str, ...],
        file_path: str,
        results: List[ConfigKey],
    ) -> None:
        for k, v in data.items():
            parts = parent_parts + (k,)
            dotted_path = ".".join(parts)
            results.append(
                ConfigKey(
                    path=dotted_path,
                    parts=parts,
                    file_path=file_path,
                    line_number=1,
                    manifest_type="toml",
                )
            )
            if isinstance(v, dict):
                cls._traverse_dict(v, parts, file_path, results)

    @classmethod
    def parse_file(cls, file_path: Path) -> List[ConfigKey]:
        keys: List[ConfigKey] = []
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return keys

        # Try tomllib first if available for full accuracy, then map line numbers
        if tomllib is not None:
            try:
                parsed = tomllib.loads(content)
                temp_keys: List[ConfigKey] = []
                cls._traverse_dict(parsed, (), str(file_path), temp_keys)
                # Map line numbers from file lines
                lines = content.splitlines()
                for tk in temp_keys:
                    leaf_key = tk.parts[-1]
                    found_line = 1
                    for line_idx, line in enumerate(lines, start=1):
                        if re.search(rf"^\s*{re.escape(leaf_key)}\s*=", line):
                            found_line = line_idx
                            break
                    keys.append(
                        ConfigKey(
                            path=tk.path,
                            parts=tk.parts,
                            file_path=tk.file_path,
                            line_number=found_line,
                            manifest_type="toml",
                        )
                    )
                return keys
            except Exception:
                pass

        # Fallback pure-regex line scanner
        lines = content.splitlines()
        current_section_parts: Tuple[str, ...] = ()

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.split("#")[0].strip()
            if not line:
                continue

            sec_match = cls.SECTION_REGEX.match(line)
            if sec_match:
                section_str = sec_match.group(1)
                current_section_parts = tuple(section_str.split("."))
                continue

            key_match = cls.KEY_REGEX.match(line)
            if key_match:
                k = key_match.group(1)
                parts = current_section_parts + (k,)
                dotted = ".".join(parts)
                keys.append(
                    ConfigKey(
                        path=dotted,
                        parts=parts,
                        file_path=str(file_path),
                        line_number=line_no,
                        manifest_type="toml",
                    )
                )

        return keys
