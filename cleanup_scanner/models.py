"""Storage-independent records and the small writer contract."""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    entry_type: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.entry_type not in {"file", "directory"}:
            raise ValueError("entry_type must be file or directory")
        if not Path(self.path).is_absolute():
            raise ValueError("Finding paths must be absolute")
        if {"path", "entry_type"} & self.metadata.keys():
            raise ValueError("Metadata cannot overwrite path or entry_type")
        json.dumps(self.metadata, allow_nan=False)

    def to_dict(self) -> dict:
        return {"path": self.path, "entry_type": self.entry_type, **self.metadata}


@dataclass(frozen=True)
class RunContext:
    started_at: datetime
    output_dir: Path


@dataclass(frozen=True)
class Problem:
    path: str
    cause: str

    def __str__(self):
        return f"{self.path}: {self.cause}"


@dataclass
class OutputResult:
    paths: list[Path] = field(default_factory=list)
    errors: list[Problem] = field(default_factory=list)


class ResultWriter(Protocol):
    def start_run(self, context: RunContext, categories: list[str]) -> None: ...
    def write_finding(self, finding: Finding) -> None: ...
    def finish_run(self) -> OutputResult: ...
