"""Validate the complete configuration before traversal or output side effects."""

from dataclasses import dataclass
from pathlib import Path
import re
import stat
import tomllib


class ConfigError(ValueError):
    """An invalid configuration that must prevent analysis."""


def is_link(path: Path) -> bool:
    """Include Windows junctions (also on Python 3.11)."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


@dataclass(frozen=True)
class Rule:
    category: str
    kind: str
    target: str
    extension: str | None = None
    name: str | None = None
    pattern: re.Pattern | None = None


@dataclass(frozen=True)
class Config:
    root: Path
    output_dir: Path
    rules: tuple[Rule, ...]
    output_format: str = "jsonl"


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a nonempty string")
    return value


def load_config(path: Path) -> Config:
    try:
        path = path.absolute()
        with path.open("rb") as source:
            data = tomllib.load(source)
        unknown = data.keys() - {"root", "output_dir", "output_format", "rules"}
        if unknown:
            raise ConfigError(f"Unknown configuration fields: {sorted(unknown)}")
        if data.get("output_format", "jsonl") != "jsonl":
            raise ConfigError("output_format must be 'jsonl'; other writers are not implemented")
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, dict) or not raw_rules:
            raise ConfigError("rules must contain at least one named rule table")
        rules = []
        if len({key.casefold() for key in raw_rules}) != len(raw_rules):
            raise ConfigError("Rule categories must be unique ignoring case for portable filenames")
        for category, values in raw_rules.items():
            try:
                rules.append(_rule(category, values))
            except ConfigError as exc:
                raise ConfigError(f"Rule {category!r}: {exc}") from exc
        raw_root = path.parent / _text(data, "root")
        if is_link(raw_root):
            raise ConfigError(f"Scan root must not be a symbolic link or junction: {raw_root}")
        root = raw_root.resolve(strict=True)
        if not root.is_dir():
            raise ConfigError(f"Scan root is not a directory: {root}")
        output = (path.parent / _text(data, "output_dir")).resolve()
        if output == root or root in output.parents:
            raise ConfigError("Invalid output_dir: output directory must be outside the scanning directory")
        return Config(root, output, tuple(rules))
    except ConfigError:
        raise
    except (OSError, ValueError, RuntimeError, re.error) as exc:
        raise ConfigError(f"Invalid configuration {path}: {exc}") from exc


def _rule(category: str, values: dict) -> Rule:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", category):
        raise ConfigError("category must contain only letters, digits, underscores, or hyphens")
    # Prefixes are Windows-safe even for categories such as CON.
    if not isinstance(values, dict):
        raise ConfigError("expected a rule table")
    kind = _text(values, "kind")
    allowed = {
        "file": {"kind", "target", "extension", "pattern"},
        "directory_name": {"kind", "target", "name", "pattern"},
        "empty_directory": {"kind", "target"},
    }
    if kind not in allowed:
        raise ConfigError(f"Unknown kind: {kind}")
    if values.keys() - allowed[kind]:
        raise ConfigError(f"Unknown fields for {kind}: {sorted(values.keys() - allowed[kind])}")
    target = _text(values, "target")
    if target not in ({"file", "parent"} if kind == "file" else {"directory"}):
        raise ConfigError(f"Invalid target {target!r} for {kind}")
    extension = _text(values, "extension") if "extension" in values else None
    if extension is not None:
        extension = "." + extension.lstrip(".").casefold()
        if extension == "." or any(c in extension for c in "/\\"):
            raise ConfigError("extension must be a filename extension")
    name = _text(values, "name") if "name" in values else None
    pattern = None
    if "pattern" in values:
        try:
            pattern = re.compile(_text(values, "pattern"), re.IGNORECASE)
        except re.error as exc:
            raise ConfigError(f"Invalid regex: {exc}") from exc
    if kind == "file" and extension is None and pattern is None:
        raise ConfigError("file rule needs extension or pattern")
    if kind == "directory_name" and name is None and pattern is None:
        raise ConfigError("directory_name rule needs name or pattern")
    return Rule(category, kind, target, extension, name, pattern)
