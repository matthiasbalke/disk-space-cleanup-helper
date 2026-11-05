# Proposal

## Why

Large directory trees need to be reviewed by content category before cleanup. A configurable, read-only scanner will identify relevant files and directories and produce structured results for separate review and automation.

## What Changes

- Introduce a Python 3 command-line scanner for Windows and Linux, configured through TOML.
- Traverse the root and its descendants once without following symbolic links, isolating filesystem errors.
- Detect directories containing CR2 files, empty directories, export subdirectories, and MP4 files matching a configurable date-prefix regex.
- Write sorted, unique structured findings to separate timestamped JSONL files in an output directory outside the scan root.
- Separate detection from storage through a small writer interface, allowing a future SQLite implementation.
- Leave size aggregation, ranking, SQLite storage, deletion, and moving files outside this first version.

## Capabilities

### New Capabilities

- `directory-analysis`: Configuration, validated scan boundaries, traversal, extensible finding rules, and error reporting.
- `finding-output`: Structured records, per-category JSONL exports, timestamped run separation, and replaceable result writers.

### Modified Capabilities

None; this repository has no existing capability specifications.

## Impact

This is a greenfield application; the repository currently contains OpenSpec setup and agent instructions only. Adds application packaging, CLI, TOML configuration examples, tests, and Windows/Linux validation. No files in the scanned tree are modified. Initial operation needs Python but no database service.
