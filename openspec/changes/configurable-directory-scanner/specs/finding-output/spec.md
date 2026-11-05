# Spec Delta

## Purpose

Persist categorized findings as structured records suitable for automation, with independently reviewable results for each analysis run.

## ADDED Requirements

### Requirement: Structured JSONL records
The initial output SHALL be UTF-8 JSON Lines, with one JSON object per finding. Every record SHALL contain an absolute native path in `path` and `entry_type` equal to `file` or `directory`. Records SHALL support optional metadata fields. Files SHALL contain no headers, summary records, or run metadata.

#### Scenario: Directory finding
- **WHEN** a directory containing CR2 files is exported
- **THEN** its record contains the directory path and entry_type directory

#### Scenario: Special characters
- **WHEN** a matched path contains Unicode, quotes, backslashes, or a newline supported by the filesystem
- **THEN** JSON escaping preserves the path on one physical line and parsing reconstructs the original path

### Requirement: Separate sorted unique category outputs
Each enabled finding type SHALL have its own result file, including an empty file when there are no findings. Records SHALL be unique by exact absolute path within each category and sorted ascending by path using case-sensitive Unicode code-point order. Matching case-insensitively SHALL NOT merge distinct filesystem paths.

#### Scenario: Duplicate findings
- **WHEN** multiple matches cause a directory to be reported repeatedly in one category
- **THEN** its path occurs only once in that category's sorted output

#### Scenario: No findings
- **WHEN** a finding type produces no records
- **THEN** its successfully written result file is empty

### Requirement: Timestamped run separation
Result filenames SHALL include the finding type and a filesystem-safe UTC start timestamp shared by all categories in a run. Repeated runs SHALL preserve earlier results. Name collisions SHALL be disambiguated without overwriting an existing result file.

#### Scenario: Multiple categories
- **WHEN** one run writes several result files
- **THEN** every filename contains the same run-start timestamp and its respective category

#### Scenario: Timestamp collision
- **WHEN** a new run would reuse existing output filenames
- **THEN** a shared run suffix distinguishes its files and earlier results remain unchanged

### Requirement: Output error isolation and completion
An output failure SHALL identify the affected file and cause and SHALL NOT prevent attempts to write other categories. The user SHALL be told which files were successfully written and when analysis is complete, with failures clearly indicated. A partially written file SHALL NOT be announced as successfully written.

#### Scenario: One category cannot be written
- **WHEN** writing one category fails
- **THEN** other categories are still attempted and completion reports both successful files and the failure

### Requirement: Storage-independent findings
Finding detection SHALL produce structured records independently of output storage. A writer SHALL support run initialization, category-specific record acceptance, and finalization. Adding another writer SHALL NOT require changes to finding rules. Initial delivery SHALL provide JSONL only.

#### Scenario: Alternative writer
- **WHEN** a different writer is selected in an integration test
- **THEN** unchanged detection logic supplies the same categories, paths, entry types, and metadata to that writer

#### Scenario: Future size metadata
- **WHEN** a writer receives a record containing size_bytes, size_scope, and complete fields
- **THEN** the JSONL writer preserves those fields without changing detection or the base record format
