# Design

## Context

The repository has no application code, build configuration, or tests. See proposal.md for motivation and the two capability deltas for behavior. The agreed stack is Python 3 and TOML, with a Windows/Linux CLI and JSONL results.

## Goals / Non-Goals

**Goals:** Keep traversal, finding evaluation, and result storage independent. Share one directory enumeration across rules. Preserve structured metadata without coupling detection to JSON serialization.

**Non-Goals:** SQLite implementation, size collection or aggregation, parallel traversal, deletion, and a GUI. Do not introduce a general plugin framework or database abstraction beyond the small writer contract.

## Decisions

### Python CLI and TOML

Proposed baseline: Python 3.11 or newer for standard-library TOML reading. Use argparse, tomllib, re, and os.scandir; avoid runtime dependencies initially. Node.js was considered; Python was selected for familiar, concise filesystem and rule code. Use a packaged CLI with a module entry point and a required --config argument, so shell differences are limited to quoting paths.

Resolve relative root/output paths against the configuration file's parent, not the invoking shell's current directory. Provide an example TOML with root, output_dir, output_format = 'jsonl', and named rule tables with kind, target, extension/name/pattern as applicable. Initial kinds cover file matches reporting files or their parent, directory-name matches reporting subdirectories, and empty-directory state. Reject unknown kinds, unsupported formats, malformed fields, duplicate/unsafe category identifiers, and invalid regex before traversal. Category identifiers are restricted to filename-safe letters, digits, underscores, and hyphens.

Compile regex once with case-insensitive flags and apply it to the basename using search; anchors in the configured expression control prefix/full-name behavior. The example dated-MP4 pattern uses an anchored year with optional month and day followed by a literal space, plus a separate MP4 extension constraint. Patterns define shape, not valid calendar dates. TOML literal strings avoid backslash escaping.

### Validate paths before side effects

Resolve root and output aliases and compare path components with native OS semantics; never use a string-prefix containment test. Reject output equality or containment, including existing symlink/junction aliases. Validate the root as an accessible real directory. Proposed conservative link policy: reject a link as the configured scan root and skip symlinks and Windows junctions during traversal. An absent valid output directory may be created after validation; creation failures are reported as output failures.

### One iterative traversal

Use an explicit stack rather than recursive Python calls, with one scoped scandir iterator per directory. Share directory-entry classification across applicable rules. Track whether any entry was seen and whether enumeration completed; only a fully enumerated directory with zero entries is empty. Avoid following links when classifying entries. Catch enumeration and per-entry errors separately and continue reachable work. Do not request file sizes in the first version.

Finding rules receive file/directory events and a directory completion state, and return records whose target is explicitly defined. Directory summaries leave room for later postorder aggregation, but no aggregation machinery is implemented now. Parent CR2 findings can be emitted once on the first matching child while remaining entries continue through other rules.

### Small writer contract and record model

Use a finding record with category, absolute native path, entry_type, and optional JSON-compatible metadata. Reserve path and entry_type against metadata collisions. The writer contract is start_run(context, categories), write_finding(record), and finish_run(), returning successful output paths and errors. Run context includes one UTC start instant and output directory. The scanner neither constructs filenames nor serializes records. A recording test writer verifies this boundary; future SQLite can map records and run context to tables without changing rules.

JSONL initially buffers records by category and exact path, sorts by Unicode code-point path order at finalization, and emits UTF-8 objects. Different case-sensitive paths remain distinct even though matching is case-insensitive. Metadata is serialized as additional fields; no run/header objects are emitted. Future size records can carry size_bytes, size_scope, and complete; their aggregation semantics and ranking remain a separate change.

### Run naming and isolated publication

Use names such as directories_with_cr2_2026-11-05T143000123456Z.jsonl, sharing the UTC start timestamp across all categories. Add a shared collision suffix when necessary and never overwrite previous runs. Write each category independently, including zero-byte outputs, using exclusive creation and removing an incomplete file on failure where possible. Collect successes and errors rather than raising a category failure through the whole run. Report diagnostics on stderr, successful paths and completion on stdout. Proposed exit statuses: 0 clean completion, 1 completion with scan/output errors, 2 invalid configuration. Do not describe a partial run as clean.

## Risks / Trade-offs

- Buffering unique findings consumes memory proportional to results → document the initial limit; future external sorting or SQLite can reduce memory pressure without changing detection.
- Filesystem contents can change during analysis → report access/disappearance errors; this is an observation, not an atomic filesystem snapshot.
- Very deep trees and OS path limits → iterative traversal avoids Python recursion limits; report native path errors and continue.
- Arbitrary regex can be expensive → compile once, document the chosen Python regex semantics, and avoid claiming bounded execution time.
- Windows links and case behavior differ from Linux → test native containment and junction behavior on Windows in addition to Linux fixtures.
- A future size report needs descendant aggregation and incomplete totals → retain optional record metadata now; specify counting, hard links, completeness, and ranking in that future change.

## Migration Plan

No existing application or data format requires migration. Deliver CLI installation instructions, example TOML, output examples, and platform tests together. Rollback removes the installed application; previously generated reports remain ordinary files. Existing business prose about plain paths and in-file timestamps is superseded by JSONL records and timestamps in filenames only.
