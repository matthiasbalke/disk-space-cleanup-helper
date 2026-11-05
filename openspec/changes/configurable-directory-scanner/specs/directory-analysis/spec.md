# Spec Delta

## Purpose

Analyze a configured directory tree without modifying it, and classify files and directories for separate review and processing.

## ADDED Requirements

### Requirement: File-based command-line configuration
The program SHALL accept a TOML configuration file through a command-line argument on Windows and Linux. Configuration SHALL specify the root, output directory, and finding rules, including filename regex patterns. Invalid configuration or regex syntax SHALL produce a clear error before scanning or writing results.

#### Scenario: Invoke from supported shells
- **WHEN** a user invokes the program with valid configuration from cmd, PowerShell, Bash, or Zsh on a supported OS
- **THEN** the program loads the configuration without requiring an interactive interface

#### Scenario: Invalid regex
- **WHEN** a configured regex cannot be compiled
- **THEN** the program identifies the invalid rule and performs no scan or result writes

### Requirement: Valid scan and output boundaries
The program MUST reject a missing or non-directory root. The output directory MUST be outside the root; equality or containment, including aliases resolved through links, SHALL produce a clear invalid-configuration error before any scan or result writes.

#### Scenario: Missing root
- **WHEN** the configured root does not exist
- **THEN** the user is told that the root is invalid and nothing is scanned

#### Scenario: Output inside root
- **WHEN** the output directory equals the root or resolves to a descendant of it
- **THEN** the program explains that output must be outside the scanning directory and stops before scanning or writing

#### Scenario: Sibling output directory
- **WHEN** the root and output directory are distinct siblings
- **THEN** the output location passes the containment check

### Requirement: Recursive traversal includes root
The program SHALL evaluate the root and every reachable descendant directory without a configured depth limit. It SHALL NOT follow symbolic links. It SHALL enumerate each directory once and evaluate each file or directory name at most once per applicable finding type.

#### Scenario: Root and nested findings
- **WHEN** matching entries exist directly under the root and in deeply nested directories
- **THEN** findings from both locations are included

#### Scenario: Symbolic link cycle
- **WHEN** a descendant entry is a symbolic link to a directory or file
- **THEN** the linked target is not traversed or evaluated as a regular file or directory

### Requirement: Directories containing CR2 files
The program SHALL report a directory when it directly contains at least one regular file with a case-insensitively matched .cr2 extension.

#### Scenario: Multiple RAW images
- **WHEN** a directory contains a.CR2 and b.cr2
- **THEN** that directory is reported once

### Requirement: Completely empty directories
The program SHALL report a directory as empty only when successful enumeration establishes that it contains no entries. Links and other filesystem entries SHALL prevent an empty classification.

#### Scenario: Directory with no entries
- **WHEN** the root or a descendant directory contains no entries
- **THEN** that directory is reported as empty

#### Scenario: Only a subdirectory or link
- **WHEN** a directory contains a subdirectory or symbolic link but no regular files
- **THEN** the containing directory is not reported as empty

### Requirement: Export subdirectories
The program SHALL report the subdirectory itself when an examined directory directly contains a real subdirectory named export, matched case-insensitively.

#### Scenario: Mixed case export
- **WHEN** a directory contains a subdirectory named ExPoRt
- **THEN** the path to ExPoRt is reported rather than its parent

### Requirement: Configurable dated MP4 matching
The program SHALL report regular MP4 file paths whose basenames match the configured filename regex. Filename and extension matching SHALL be case-insensitive. The supplied example pattern SHALL accept year, year-month, or full date prefixes followed by a literal space. Calendar validation SHALL NOT be imposed beyond the configured regex.

#### Scenario: Supported prefixes
- **WHEN** the example rule encounters 2024 clip.mp4, 2024-03 clip.MP4, and 2024-03-21 clip.mp4
- **THEN** it reports each file path rather than its containing directory

#### Scenario: Nonmatching video
- **WHEN** a file has an MP4 extension but does not match the configured regex
- **THEN** it is not included in this finding type

### Requirement: Recoverable scan problems
A filesystem problem at one location SHALL be reported with its path and cause, and SHALL NOT stop analysis of other accessible locations. Incomplete enumeration SHALL NOT establish that a directory is empty. Completion reporting SHALL distinguish a clean run from a run with errors.

#### Scenario: Unreadable directory
- **WHEN** a directory cannot be fully enumerated
- **THEN** an error is reported, that directory is not classified as empty, and accessible sibling directories are still examined

### Requirement: Extensible finding types
The program SHALL support adding finding types based on file names, directory names, or directory state. Each type SHALL define whether its results identify a file, the examined directory, or a contained subdirectory, without requiring another traversal.

#### Scenario: Additional filename rule
- **WHEN** a new filename-based finding type is added
- **THEN** it can report matching file paths using entries from the existing traversal
