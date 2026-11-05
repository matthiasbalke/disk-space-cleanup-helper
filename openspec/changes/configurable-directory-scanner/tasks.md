# Tasks

## 1. CLI and configuration

- [ ] 1.1 Create Python 3.11+ package metadata, CLI and module entry points; verify installation and --help work.
- [x] 1.2 Implement TOML loading, config-relative path resolution, finding-rule validation, and case-insensitive regex compilation; verify valid and invalid configuration tests, including malformed regex and unsafe category names.
- [x] 1.3 Validate root existence/type and resolved output containment before side effects; verify equality, nested output, sibling prefixes, missing roots, and link aliases using tests.
- [x] 1.4 Deliver an example TOML for all four finding types and CLI/configuration documentation; verify the example loads and document shell quoting and relative-path semantics.

## 2. Shared traversal and finding rules

- [x] 2.1 Implement iterative single-enumeration traversal with no symlink or Windows junction following and isolated entry/directory errors; verify deep fixtures, link cycles, interrupted enumeration, and instrumented enumeration counts.
- [x] 2.2 Implement CR2-parent, empty-directory, export-subdirectory, and configurable MP4-file rules over shared entries; verify root inclusion, mixed case, date-prefix shapes, nonmatching MP4s, report targets, and no repeated name evaluation per rule.
- [x] 2.3 Document rule kinds, targets, Python regex semantics, and how to add a finding type; verify an additional test rule uses the same traversal without scanner changes.

## 3. Records and output writers

- [x] 3.1 Define structured findings, optional metadata, run context, and the start/accept/finalize writer contract; verify a recording writer receives the same findings independently of storage and reserved fields cannot be overwritten.
- [x] 3.2 Implement JSONL serialization with exact-path deduplication and documented path sorting per category; verify round-trip special characters, optional size metadata, distinct case-sensitive paths, no header records, and zero-byte files for empty categories.
- [x] 3.3 Implement shared UTC run-start filename timestamps, collision disambiguation, and independent exclusive file writes; verify repeated runs preserve earlier outputs and one injected write failure does not block other category files or report partial output as successful.
- [x] 3.4 Document the JSONL record contract, timestamp naming, memory tradeoff, and future writer extension; verify examples parse as JSON and distinguish future SQLite/size support from delivered features.

## 4. Integration and platform acceptance

- [x] 4.1 Connect CLI validation, traversal, writers, and completion reporting with documented exit statuses; verify subprocess tests for clean runs, invalid configuration, partial scan errors, and output failures, including no result writes for invalid configuration.
- [ ] 4.2 Add Windows and Linux CI coverage for the full acceptance suite, including native path containment, junction/link behavior where supported, and Unicode names; verify both platform jobs pass and explain any capability-dependent skips.
- [x] 4.3 Run an end-to-end fixture with all four categories and a representative large synthetic tree; verify expected records, stable category outputs, single-pass enumeration, and document observed performance without promising hardware-independent timings.
