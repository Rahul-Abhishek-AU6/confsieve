"""Zero-dependency structural YAML key parser with line number tracking."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from ..core import ConfigKey


class YamlParser:
    """Parses YAML configuration files without external dependencies."""

    KEY_REGEX = re.compile(r"^(\s*)([\'\"]?[\w\-\.\/]+[\'\"]?)\s*:(?:\s*(.*))?$")

    @classmethod
    def parse_file(cls, file_path: Path) -> List[ConfigKey]:
        keys: List[ConfigKey] = []
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return keys

        # Stack of (indent_level, key_name)
        stack: List[Tuple[int, str]] = []

        for line_no, raw_line in enumerate(lines, start=1):
            # Strip comments that are not inside quotes
            comment_idx = raw_line.find("#")
            line = raw_line if comment_idx == -1 else raw_line[:comment_idx]

            # Skip blank or pure comment lines
            if not line.strip():
                continue

            # Skip YAML document separators
            if line.strip() in ("---", "..."):
                stack.clear()
                continue

            # Skip list items that are purely scalar
            trimmed = line.lstrip()
            if trimmed.startswith("- "):
                # If it's a list item containing a key-value pair, e.g. "- name: foo"
                line = " " * (len(line) - len(trimmed) + 2) + trimmed[2:]

            match = cls.KEY_REGEX.match(line)
            if not match:
                continue

            indent_str, raw_key, rest = match.groups()
            indent = len(indent_str)

            # Clean key quotes
            key_name = raw_key.strip("'\"")

            # Pop stack entries with greater or equal indentation
            while stack and stack[-1][0] >= indent:
                stack.pop()

            # The current parts path
            parent_parts = tuple(item[1] for item in stack)
            current_parts = parent_parts + (key_name,)
            dotted_path = ".".join(current_parts)

            keys.append(
                ConfigKey(
                    path=dotted_path,
                    parts=current_parts,
                    file_path=str(file_path),
                    line_number=line_no,
                    manifest_type="yaml",
                )
            )

            # If this key might have children (empty rest, or block mapping)
            # push to stack
            if rest is None or rest.strip() == "" or rest.strip().startswith("|") or rest.strip().startswith(">"):
                stack.append((indent, key_name))

        return keys
