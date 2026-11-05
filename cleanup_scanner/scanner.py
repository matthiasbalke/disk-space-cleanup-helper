"""Single-pass traversal; neither filenames for reports nor serialization live here."""

import os
from pathlib import Path
import stat

from .models import Problem, ResultWriter
from .rules import DirectoryState, Entry


def scan(root: Path, rules, writer: ResultWriter) -> list[Problem]:
    errors = []
    pending = [root]
    while pending:
        directory = pending.pop()
        has_entries = False
        complete = False
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    has_entries = True
                    try:
                        if entry.is_symlink():
                            continue
                        # Junctions are reparse points but not necessarily symlinks.
                        if os.name == "nt" and (
                            getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                            & stat.FILE_ATTRIBUTE_REPARSE_POINT
                        ):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            entry_type = "directory"
                        elif entry.is_file(follow_symlinks=False):
                            entry_type = "file"
                        else:
                            continue
                    except OSError as exc:
                        errors.append(Problem(entry.path, str(exc)))
                        continue
                    event = Entry(Path(entry.path), entry_type)
                    if entry_type == "directory":
                        pending.append(event.path)
                    for rule in rules:
                        for finding in rule.on_entry(event):
                            writer.write_finding(finding)
                complete = True
        except OSError as exc:
            errors.append(Problem(str(directory), str(exc)))
        state = DirectoryState(directory, has_entries, complete)
        for rule in rules:
            for finding in rule.on_directory(state):
                writer.write_finding(finding)
    return errors
