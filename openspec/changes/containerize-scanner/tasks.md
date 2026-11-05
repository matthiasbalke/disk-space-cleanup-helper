# Tasks

## 1. Minimal non-root image

- [x] 1.1 Add a multi-stage Dockerfile using compatible digest-pinned Python/Alpine bases and an allowlisted .dockerignore; verify a clean linux/amd64 build and --help invocation succeed.
- [x] 1.2 Configure UID/GID 10001:10001, numeric-user overrides, exec-form CLI startup, and no runtime privilege changes; verify default effective IDs are nonzero and an arbitrary non-root identity runs without an account entry.
- [x] 1.3 Exclude packaging tools, compilers, tests, caches, history, and planning artifacts from runtime; add filesystem checks and an 80 MiB uncompressed size gate, verifying the image inspection measurement and negative oversized-candidate case.
- [x] 1.4 Add a container-specific TOML example and Docker documentation for Linux shells and PowerShell, including separate mounts, UID/GID permissions, container-path results, image architecture, and Docker Desktop Linux mode; verify documented commands against a fixture.

## 2. Container behavior verification

- [x] 2.1 Add container integration tests for the four finding types, timestamped JSONL, Unicode names, ordering, uniqueness, empty categories, persisted host reports, and unchanged input; verify tests pass against the final runtime image.
- [x] 2.2 Test read-only configuration/input/rootfs, dropped capabilities, no-new-privileges, and no network using default and overridden non-root users; verify valid runs succeed and invalid configuration or unwritable output preserve exit statuses 2 or 1.
- [x] 2.3 Document local build/test commands and measured runtime size; verify existing application unit tests and container acceptance tests run independently and together.

## 3. GitHub validation and GHCR publishing

- [x] 3.1 Add push-to-main and pull-request validation with unit tests, Buildx build/load, container acceptance checks, and image-size reporting; verify workflow structure and successful read-only validation without publishing on a pull request.
- [ ] 3.2 Pass the tested image archive to a dependent main-only publish job, authenticate using GITHUB_TOKEN with job-scoped contents:read and packages:write, and publish lowercase latest and sha-<full SHA> tags with OCI labels; verify the workflow does not rebuild and PRs receive no publish permissions.
- [x] 3.3 Serialize main publication and skip superseded candidates; verify overlapping-run logic cannot move latest back to an older commit and document current-main-only publication behavior.
- [ ] 3.4 Document GHCR image references, digest pinning, package access/visibility, and publication diagnostics; verify the first successful main run publishes both expected tags, reports their digest, and the published image can be pulled and smoke-tested.
