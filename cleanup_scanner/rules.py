"""Rules consume shared entry and directory-completion events."""

from dataclasses import dataclass
from pathlib import Path

from .config import Rule
from .models import Finding


@dataclass(frozen=True)
class Entry:
    path: Path
    entry_type: str


@dataclass(frozen=True)
class DirectoryState:
    path: Path
    has_entries: bool
    complete: bool


class FindingRule:
    def __init__(self, rule: Rule):
        self.rule = rule
        self.category = rule.category

    def on_entry(self, entry: Entry):
        rule = self.rule
        applicable = "file" if rule.kind == "file" else "directory"
        if rule.kind == "empty_directory" or entry.entry_type != applicable:
            return
        name = entry.path.name
        if rule.extension and entry.path.suffix.casefold() != rule.extension:
            return
        if rule.name and name.casefold() != rule.name.casefold():
            return
        if rule.pattern and not rule.pattern.search(name):
            return
        path = entry.path.parent if rule.target == "parent" else entry.path
        entry_type = "directory" if rule.target == "parent" else entry.entry_type
        yield Finding(rule.category, str(path), entry_type)

    def on_directory(self, state: DirectoryState):
        if self.rule.kind == "empty_directory" and state.complete and not state.has_entries:
            yield Finding(self.category, str(state.path), "directory")
