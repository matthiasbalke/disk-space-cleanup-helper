# Disk space cleanup helper

A read-only directory scanner for Python 3.11+ on Windows and Linux. It reports
CR2-containing directories, completely empty directories, export subdirectories,
and dated MP4 files. It never deletes or moves scanned content.

## Install and run

```sh
python -m pip install .
cleanup-scan --config "path/to/scan.toml"
```

Alternatively run `python -m cleanup_scanner --config "path/to/scan.toml"` from
this repository. Use `python3` on Linux if needed. Both entry points support
`--help`. These commands work from cmd, PowerShell, Bash, and Zsh; quote paths
containing spaces using the quoting rules of your shell.

## Configuration

Copy [examples/scan.toml](examples/scan.toml) and edit `root` and `output_dir`.
Relative paths resolve against the configuration file's directory. Output must
be outside the scan root: equality and descendants are rejected before scanning
or creating reports. Root must exist and be a directory, not a symlink or junction.
A missing valid output directory is created when reports are written.

Named `[rules.category]` tables define separate result categories:

| kind | target | Matching fields |
| --- | --- | --- |
| `file` | `file` or `parent` | `extension`, `pattern`, or both |
| `directory_name` | `directory` | `name`, `pattern`, or both |
| `empty_directory` | `directory` | None |

When multiple matching fields are supplied, all must match. Names and extensions
match without case sensitivity on both operating systems. Patterns use Python
regular expressions with `IGNORECASE` and `search` against the basename; use `^`
for a prefix and `$` for an end anchor. TOML single-quoted literal strings avoid
extra backslash escaping. Invalid regex or configuration stops the run before
scanning or writing results. Category identifiers use letters, digits, `_`, or `-`.

The example date pattern accepts year, year-month, or full date followed by a
literal space. It validates the shape only, not actual calendar dates. MP4 files
without a matching prefix are ignored. Matching MP4s report the file itself;
CR2 rules report the immediate parent, not all ancestors. Export rules report
the matching subdirectory. The root itself is evaluated, including for emptiness.

## Results and errors

Each configured category gets a JSONL file, even when there are no matches.
For example: `directories_with_cr2_2026-11-05T143000123456Z.jsonl`. All categories
share the UTC run-start timestamp. Collisions add a shared suffix such as `_1`;
earlier runs are never overwritten. There is no append or overwrite mode.

Each line is a finding object, with no headers or run metadata:

```json
{"path": "/photos/holiday", "entry_type": "directory"}
```

Paths are absolute and native to the scanning OS. JSON escapes special
characters, including embedded newlines; use a JSON parser to recover the path.
Records are unique by exact path within each category and sorted by case-sensitive
Unicode code-point path order. Matching ignores case, but distinct paths on a
case-sensitive filesystem are preserved. Empty categories produce empty files.

The root and descendants are enumerated once. Symbolic links and Windows
junctions/reparse points are skipped; a directory containing only a link is not
empty. Access failures are reported with their location; accessible locations and
other output categories continue. Incomplete enumeration cannot prove emptiness.
The filesystem can change during a run; results are not an atomic snapshot.

Successful output paths and completion appear on stdout; errors appear on stderr.
Exit status is `0` for success, `1` for completion with scan/output errors, and `2`
for invalid configuration/arguments. Partial output files are removed when possible
and never announced as successful. If output directory creation fails, all category
output failures are reported after scanning.

## Extending the scanner

Add configured rules of the existing kinds without changing the scanner. For a
new kind, extend configuration validation and implement `on_entry(Entry)` and
`on_directory(DirectoryState)` in a rule object, yielding `Finding` records.
`DirectoryState` exposes path, whether any entries were seen, and whether enumeration
completed. Do not enumerate directories again inside a rule. The scanner dispatches
each real entry to each rule once and one completion event per directory.

Storage is separate: `ResultWriter` defines `start_run(context, categories)`,
`write_finding(finding)`, and `finish_run()`. Finalization returns output paths and
errors. `app.run(config, writer=...)` accepts another writer without changing rules.
Only JSONL is currently implemented; SQLite is a future extension.

Findings support optional JSON-compatible metadata alongside `path` and `entry_type`.
These reserved fields cannot be replaced. A future size report could emit:

```json
{"path": "/photos/holiday", "entry_type": "directory", "size_bytes": 1837468210, "size_scope": "recursive", "complete": true}
```

Size collection, descendant aggregation, ranking, hard-link counting, and SQLite
storage are not implemented. JSONL currently buffers unique findings in memory to
sort them; memory grows with the number of results. There is no fixed capacity
limit beyond available memory. Future external sorting or a SQLite writer can
address larger inventories. Regex patterns are compiled once, but expensive
user-defined expressions can still slow a scan.

## Development and verification

```sh
python -m unittest discover -v
python -m tests.benchmark
```

Unit and CLI integration tests cover validation, links, errors, deduplication,
metadata, special characters, timestamps, and alternative writers. GitHub Actions
runs the suite and packaging smoke checks on Windows and Linux with Python 3.11
and 3.13. Windows junction tests run on Windows; POSIX permission tests run on Linux.
Symlink tests skip with a reason when the account lacks symlink privileges.

A synthetic Linux/Python 3.13 run in the development sandbox examined 2,001
directories and 11,000 zero-byte files, producing 4,000 findings in 0.274 seconds
(including analysis and writing; excluding fixture creation). Instrumentation
confirmed one enumeration per directory. This is a reproducible smoke benchmark,
not a prediction for real disks, network storage, or other machines.

## Docker

The container image is `ghcr.io/matthiasbalke/disk-space-cleanup-helper:latest`
(linux/amd64). Windows users need Docker Desktop in Linux-container mode. It
runs as UID/GID `10001:10001`, never elevates privileges, and needs no network.
The default command displays help. To analyze data, copy
[examples/container.toml](examples/container.toml) to a separate configuration
directory as `scan.toml`. It uses `/data` for input and `/output` for results.

Create three separate host directories for configuration, input, and output.
The output directory must not physically reside within input, even if separate
bind mounts hide this relationship. Configuration and input mounts are read-only.
Reports contain **container paths**, e.g. `/data/holiday`, corresponding to
`holiday` beneath your host input directory. They do not contain host paths.

Bash/Zsh on Linux (run as a non-root host user):

```sh
mkdir -p "$PWD/reports"
docker run --rm --read-only --network=none --cap-drop=ALL \
  --security-opt=no-new-privileges --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$PWD/config,target=/config,readonly" \
  --mount "type=bind,source=$PWD/photos,target=/data,readonly" \
  --mount "type=bind,source=$PWD/reports,target=/output" \
  ghcr.io/matthiasbalke/disk-space-cleanup-helper:latest \
  --config /config/scan.toml
```

The output directory must be writable by the chosen UID/GID and input must be
readable/searchable by it. To use the default image identity on Linux instead,
grant UID/GID 10001 appropriate ownership or ACL access before running; startup
does not change host ownership or permissions. Avoid world-writable directories.
Numeric `--user UID:GID` overrides work without an account entry in the image.

PowerShell with Docker Desktop (replace these absolute host paths):

```powershell
New-Item -ItemType Directory -Force 'C:\scanner\reports' | Out-Null
docker run --rm --read-only --network=none --cap-drop=ALL `
  --security-opt=no-new-privileges `
  --mount 'type=bind,source=C:\scanner\config,target=/config,readonly' `
  --mount 'type=bind,source=C:\photos,target=/data,readonly' `
  --mount 'type=bind,source=C:\scanner\reports,target=/output' `
  ghcr.io/matthiasbalke/disk-space-cleanup-helper:latest `
  --config /config/scan.toml
```

All source directories must already exist and Docker Desktop must have access to
them. Docker Desktop mediates Windows file permissions; Linux UID mapping does
not translate directly to Windows accounts. Configuration paths still use Linux
syntax inside the container. Results persist after the container exits. Native
Python installation continues to work on Windows and Linux.

### Building and testing the image

```sh
docker buildx build --platform linux/amd64 --load -t cleanup-scanner:test .
python -m unittest discover -s tests -v
SCANNER_IMAGE=cleanup-scanner:test python -m unittest container_tests.test_image -v
```

For PowerShell, set `$env:SCANNER_IMAGE = 'cleanup-scanner:test'` before invoking
the container test command (the integration fixture currently requires a Linux
host for UID-based permission preparation; it runs on Linux CI). Native unit
tests run on both Windows and Linux. Run `SCANNER_IMAGE=cleanup-scanner:test
python -m unittest discover -v` on Linux to execute both suites together.

The runtime contains the interpreter, required runtime libraries, and the
application, excluding pip, setuptools, compilers, tests, caches, and repository
files. Base images are digest-pinned; refresh both compatible Alpine/Python
bases together and rerun acceptance tests when updating them. CI measures
uncompressed image size with `docker image inspect` and enforces an 80 MiB
(83,886,080 bytes) ceiling. Registry compressed transfer size is a different
measurement. Container acceptance tests check the default and overridden
non-root users, read-only rootfs/input/config, no capabilities or network,
JSONL contents, and configuration/output failure exit codes.

### Publishing and selecting versions

Every push to `main` builds and validates the image before publication to GHCR.
Pull requests build and test without logging in or publishing. The publish job
loads the exact validated image archive without rebuilding it. It alone receives
`packages:write`, authenticating with `GITHUB_TOKEN`; no PAT is needed.

Published tags are `latest` and `sha-<full-commit-sha>`. OCI labels identify the
source repository and revision. Publication is serialized and superseded main
candidates are skipped, so an old run cannot regress `latest`. The workflow
summary includes size, published references, and digest. It pulls both registry
tags and runs the published image as a final check.

Use the SHA tag to select a commit, or pin the digest from the workflow summary:
`ghcr.io/matthiasbalke/disk-space-cleanup-helper@sha256:<digest>`. Roll back by
selecting an older tag/digest. GHCR packages may initially be private; maintainers
can change package visibility in GitHub's package settings if public pulls are
desired. Private pulls require `docker login ghcr.io` with an appropriately
permissioned account. A denied publish usually requires checking package linkage
and repository Actions access; a denied pull may indicate package visibility or
missing registry credentials.
