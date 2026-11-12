"""Native JSON configuration parser with hierarchical key and line tracking."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..core import ConfigKey


class JsonParser:
    """Parses JSON configuration files and extracts hierarchical keys with line numbers."""

    @classmethod
    def _find_line_number(cls, lines: List[str], key_name: str, start_line: int = 1) -> int:
        pattern = re.compile(rf'"{re.escape(key_name)}"\s*:')
        for idx in range(start_line - 1, len(lines)):
            if pattern.search(lines[idx]):
                return idx + 1
        return start_line

    @classmethod
    def _traverse(
        cls,
        data: Any,
        parent_parts: Tuple[str, ...],
        lines: List[str],
        file_path: str,
        results: List[ConfigKey],
        current_line: int = 1,
    ) -> None:
        if isinstance(data, dict):
            for k, v in data.items():
                parts = parent_parts + (k,)
                line_no = cls._find_line_number(lines, k, current_line)
                dotted_path = ".".join(parts)
                results.append(
                    ConfigKey(
                        path=dotted_path,
                        parts=parts,
                        file_path=file_path,
                        line_number=line_no,
                        manifest_type="json",
                    )
                )
                cls._traverse(v, parts, lines, file_path, results, line_no)
        elif isinstance(data, list):
            for item in data:
                cls._traverse(item, parent_parts, lines, file_path, results, current_line)

    @classmethod
    def parse_file(cls, file_path: Path) -> List[ConfigKey]:
        keys: List[ConfigKey] = []
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            lines = content.splitlines()
            cls._traverse(data, (), lines, str(file_path), keys)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return keys
        return keys
