# Proposal

## Why

Users should be able to run the scanner without installing Python on the host. A small container running without root privileges provides a repeatable CLI distribution that GitHub can build and publish automatically.

## What Changes

- Package the existing CLI as a minimal Linux container running as a regular non-root user by default.
- Accept externally mounted TOML configuration, read-only scan input, and a writable output directory; retain existing CLI behavior and exit codes.
- Keep build tools, tests, repository history, caches, and user data out of the runtime image, and enforce a measurable image-size budget.
- Build, test, and publish the image to GHCR on every push to main with latest and commit-specific tags.
- Validate container builds on pull requests without publishing or granting registry write permissions.
- Document Docker usage from Linux shells and Windows PowerShell with Docker Desktop in Linux-container mode.

## Capabilities

### New Capabilities

- `container-execution`: Minimal, non-root container distribution of the scanner with external configuration and data mounts.
- `container-publishing`: Automated validated container builds and main-branch publication to GHCR.

### Modified Capabilities

None. Existing scanning and output behavior remains defined by the completed configurable-directory-scanner change, which has not yet been archived into main specs.

## Impact

Adds Dockerfile, .dockerignore, container smoke tests, publishing workflow, and container documentation/examples. The app currently has no runtime dependencies and already supports configuration paths through --config; no detection or record-format changes are needed. Initial architecture assumption is linux/amd64; ARM and native Windows images are outside this change. No container is built or published during this proposal workflow.
