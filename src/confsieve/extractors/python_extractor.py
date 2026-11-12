"""AST-based configuration lookup extractor for Python source files."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional, Set, Tuple

from ..core import CodeLookup

DEFAULT_CONFIG_OBJECTS = {
    "config",
    "cfg",
    "settings",
    "conf",
    "app_config",
    "app.config",
    "current_app.config",
}

IGNORED_ATTRIBUTES = {
    "get", "items", "keys", "values", "copy", "clear", "update",
    "pop", "setdefault", "fromkeys", "read", "write", "load", "loads",
    "dump", "dumps", "parse", "close"
}


class ConfigVisitor(ast.NodeVisitor):
    """Walks Python AST to discover configuration lookups."""

    def __init__(
        self,
        file_path: str,
        target_objects: Optional[Set[str]] = None,
    ) -> None:
        self.file_path = file_path
        self.target_objects = target_objects or DEFAULT_CONFIG_OBJECTS
        self.lookups: List[CodeLookup] = []
        self._processed_subscripts: Set[int] = set()

    def _get_object_name(self, node: ast.AST) -> Optional[str]:
        """Resolve the full dotted name of an object expression."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parent = self._get_object_name(node.value)
            if parent:
                return f"{parent}.{node.attr}"
            return node.attr
        return None

    def _is_config_object(self, name: Optional[str]) -> bool:
        if not name:
            return False
        # Exact match or suffix match (e.g. self.config, app.config)
        if name in self.target_objects:
            return True
        for target in self.target_objects:
            if name == target or name.endswith(f".{target}"):
                return True
        return False

    def _unwrap_subscript_chain(self, node: ast.Subscript) -> Tuple[Optional[str], List[str], Optional[ast.Subscript]]:
        """Unwrap nested subscripts like config['a']['b']['c']."""
        parts = []
        curr: ast.AST = node

        while isinstance(curr, ast.Subscript):
            self._processed_subscripts.add(id(curr))
            slice_node = curr.slice
            # In Python 3.9+, ast.Constant is used for string index
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                parts.insert(0, slice_node.value)
            elif isinstance(slice_node, ast.Index) and isinstance(slice_node.value, ast.Constant) and isinstance(slice_node.value.value, str):  # type: ignore[attr-defined]
                parts.insert(0, slice_node.value.value)
            else:
                # Dynamic key or non-string index
                return None, [], None
            curr = curr.value

        obj_name = self._get_object_name(curr)
        return obj_name, parts, node

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if id(node) in self._processed_subscripts:
            self.generic_visit(node)
            return

        obj_name, parts, root_subscript = self._unwrap_subscript_chain(node)
        if obj_name and self._is_config_object(obj_name) and parts:
            dotted_path = ".".join(parts)
            self.lookups.append(
                CodeLookup(
                    path=dotted_path,
                    parts=tuple(parts),
                    file_path=self.file_path,
                    line_number=node.lineno,
                    access_type="subscript",
                    object_name=obj_name,
                )
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Handle config.get('key', default) calls."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            obj_name = self._get_object_name(node.func.value)
            if obj_name and self._is_config_object(obj_name):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    key_val = node.args[0].value
                    parts = tuple(key_val.split("."))
                    default_repr = None
                    if len(node.args) > 1:
                        if isinstance(node.args[1], ast.Constant):
                            default_repr = repr(node.args[1].value)
                        elif isinstance(node.args[1], ast.Name):
                            default_repr = node.args[1].id

                    self.lookups.append(
                        CodeLookup(
                            path=key_val,
                            parts=parts,
                            file_path=self.file_path,
                            line_number=node.lineno,
                            access_type="get",
                            object_name=obj_name,
                            default_value=default_repr,
                        )
                    )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Handle settings.DEBUG or config.PORT attribute accesses."""
        if not node.attr.startswith("_") and node.attr not in IGNORED_ATTRIBUTES:
            obj_name = self._get_object_name(node.value)
            if obj_name and self._is_config_object(obj_name):
                self.lookups.append(
                    CodeLookup(
                        path=node.attr,
                        parts=(node.attr,),
                        file_path=self.file_path,
                        line_number=node.lineno,
                        access_type="attr",
                        object_name=obj_name,
                    )
                )

        self.generic_visit(node)


class PythonExtractor:
    """Extracts configuration accesses from Python files or directories."""

    def __init__(self, target_objects: Optional[Set[str]] = None) -> None:
        self.target_objects = target_objects

    def extract_from_file(self, file_path: Path) -> List[CodeLookup]:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            visitor = ConfigVisitor(str(file_path), target_objects=self.target_objects)
            visitor.visit(tree)
            return visitor.lookups
        except (SyntaxError, UnicodeDecodeError, OSError):
            return []

    def extract_from_paths(self, paths: List[Path]) -> Tuple[List[CodeLookup], List[str]]:
        all_lookups: List[CodeLookup] = []
        scanned_files: List[str] = []

        for p in paths:
            if p.is_file() and p.suffix == ".py":
                lookups = self.extract_from_file(p)
                all_lookups.extend(lookups)
                scanned_files.append(str(p))
            elif p.is_dir():
                for py_file in p.rglob("*.py"):
                    if any(part.startswith(".") or part in ("__pycache__", "venv", ".venv") for part in py_file.parts):
                        continue
                    lookups = self.extract_from_file(py_file)
                    all_lookups.extend(lookups)
                    scanned_files.append(str(py_file))

        return all_lookups, scanned_files
