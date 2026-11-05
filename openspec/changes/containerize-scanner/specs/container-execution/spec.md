# Spec Delta

## Purpose

Distribute the directory scanner as a small container that analyzes mounted content without requiring a host Python installation or root privileges.

## ADDED Requirements

### Requirement: Container CLI compatibility
The image SHALL run the existing scanner CLI for linux/amd64, accepting --config and --help and preserving stdout, stderr, and exit statuses. The container SHALL exit when the analysis finishes.

#### Scenario: Mounted configuration
- **WHEN** the image is invoked with --config referring to a readable mounted TOML file
- **THEN** the scanner executes the configured analysis and exits with its existing result status

#### Scenario: Invalid configuration
- **WHEN** a mounted configuration places output inside the scan root
- **THEN** the container reports the existing configuration error, writes no results, and exits with status 2

### Requirement: Non-root execution
The image SHALL default to a regular non-root user with nonzero UID and GID. Startup SHALL NOT elevate privileges or require privileged container mode. Users SHALL be able to override the numeric UID and GID for host bind-mount permissions without rebuilding the image.

#### Scenario: Default identity
- **WHEN** the image is launched without a user override
- **THEN** the scanner process has nonzero effective UID and GID

#### Scenario: Host identity override
- **WHEN** a user supplies a non-root UID and GID with access to the mounted input and output
- **THEN** analysis completes without needing a named account for that identity inside the image

### Requirement: External input and output
The container SHALL support read-only configuration and input mounts and a distinct writable output mount. The image SHALL contain no user scan content or results. Report paths SHALL identify paths inside the container; documentation SHALL explain their mapping to host paths.

#### Scenario: Persisted reports
- **WHEN** a fixture containing all four finding types is scanned with read-only input and writable external output
- **THEN** valid timestamped JSONL reports remain on the host after the container is removed and input contents are unchanged

### Requirement: Minimal runtime image
The linux/amd64 image SHALL have an uncompressed image size no greater than 80 MiB as reported by Docker image inspection. Runtime contents SHALL exclude build toolchains, pip, setuptools, test code, repository history, dependency caches, and planning artifacts. CI SHALL report the measured size and reject oversized images.

#### Scenario: Size gate
- **WHEN** an image candidate exceeds 83,886,080 bytes
- **THEN** validation fails and that candidate is not published

#### Scenario: Runtime inspection
- **WHEN** the final image filesystem is inspected
- **THEN** only the runtime and application assets needed for execution are included, without the excluded development assets

### Requirement: Restricted runtime support
The scanner SHALL run with a read-only container root filesystem, all Linux capabilities dropped, no-new-privileges enabled, and networking disabled, provided the configured output mount is writable.

#### Scenario: Restricted execution
- **WHEN** a valid analysis runs with those restrictions and correctly permissioned mounts
- **THEN** it completes and persists the expected reports without modifying its root filesystem or requiring network access
