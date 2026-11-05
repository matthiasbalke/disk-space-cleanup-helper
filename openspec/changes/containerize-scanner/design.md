# Design

## Context

The existing app is a dependency-free Python 3.11+ CLI with --config and --help, TOML configuration, native absolute paths in JSONL reports, and exit statuses 0/1/2. The repository has a Windows/Linux unit-test matrix but no Dockerfile, ignore file, or publishing workflow. The earlier scanner change is complete but unarchived. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:** Ship the same CLI in a small image, keep runtime identity unprivileged, and validate the actual artifact before publication. Define a reproducible measurement for the size request rather than claim an unmeasured size.

**Non-Goals:** Scanner changes, host path translation in records, root helpers, privileged runtime, ARM images, native Windows containers, Kubernetes or Compose deployment, release-version tags, and automatic changes to GHCR package visibility.

## Decisions

### Small Alpine runtime

Use an official Python 3.13 Alpine build stage and a matching Alpine runtime stage. Install the project into an isolated location in the build stage using the existing package metadata. Copy the required interpreter/standard-library and application installation into the matching runtime with only their required shared-library runtime dependencies. Exclude pip, setuptools, compilers, headers, caches, Python tests, and other build-only assets. Preserve runtime library licenses. Do not copy arbitrary repository contents into the final image. Use .dockerignore with an explicit allowlist for packaging inputs; tests run externally or in a separate stage.

Alpine is selected over Debian slim because the app has no native dependencies and minimizing size is the priority. A full Python image includes unnecessary tooling; scratch requires more manual runtime/library maintenance. Resolve concrete supported Alpine/Python tags and pin base digests during implementation, keeping stages compatible; do not invent digests in planning. Verify Unicode paths and the complete fixture in the resulting runtime. Python must retain filesystem, regex, TOML, JSON, and datetime functionality.

Proposed acceptance budget: at most 80 MiB (83,886,080 bytes) uncompressed linux/amd64 image size from docker image inspect .Size. Report that measurement, and optionally compressed registry size separately. The bound is a ceiling, not a target to fill. CI enforces it; runtime dependency and filesystem inspection prevents meeting the budget by retaining avoidable tooling. Do not remove required modules just to pass size checks.

### Runtime identity and mounts

Create a regular scanner account with UID/GID 10001:10001, no login shell, and no privilege escalation. Set numeric USER, root-owned read/execute application files, a stable work directory, PYTHONDONTWRITEBYTECODE=1, and PYTHONUNBUFFERED=1. Use an exec-form entry point invoking the module so arguments and exit codes pass through without a shell wrapper. Default arguments display --help. No startup chown, chmod, or UID-switch helper is needed.

Document three separate mounts: configuration under /config (read-only), scan data under /data (read-only), results under /output (writable). Supply a container-specific TOML example using these absolute paths, retaining the original native example. Users pre-create the output directory and grant the chosen user write access; Linux users can use --user UID:GID to align ownership. Do not recommend world-writable permissions. The app must also work with a numeric user absent from /etc/passwd.

Use --mount to avoid silently creating misspelled source paths. Document Bash/Zsh and PowerShell quoting using absolute host paths. Windows uses Docker Desktop Linux containers; paths in TOML and reports are Linux container paths, not original Windows paths. Output must still be outside the configured root inside the container. The container cannot detect aliases hidden by separate bind mounts, so documentation must require physically separate host input/output locations too.

### Verification of the artifact

Add automated container acceptance checks driven from the host using the standard-library test tooling. Build/load linux/amd64 once, inspect size and default USER, and run an identity check through an overridden Python entry point. Run the full four-category fixture with default identity and an arbitrary numeric non-root identity, pre-permissioned output mounts, read-only rootfs, dropped capabilities, no-new-privileges, and no network. Compare decoded JSONL paths, ordering, uniqueness, empty outputs, host persistence, and unchanged input. Verify invalid configuration and unwritable output exit codes. Inspect runtime contents for excluded tooling and build assets. These are container integration tests, not replacements for existing unit tests.

### Build and publish workflow

Add a separate workflow on push to main and pull_request. A read-only validation job runs unit tests, builds the image with Buildx, loads it locally, and runs the container checks including size. On main, export that exact tested image as a Docker archive artifact. A dependent publish job with contents:read and packages:write downloads and loads it, authenticates to ghcr.io with github.actor and GITHUB_TOKEN, tags it as latest and sha-<full SHA>, and pushes both. No rebuild occurs between validation and publication. PRs neither upload a publish artifact nor run the publish job. Keep existing native Windows/Linux CI intact.

Derive the lowercase image path from github.repository; here it is ghcr.io/matthiasbalke/disk-space-cleanup-helper. Apply OCI source/revision labels when building. Capture pushed digests and references in the job summary. Pin third-party action revisions during implementation and use only the permissions each job needs.

Use a workflow concurrency group for main publication with cancel-in-progress false so publication jobs do not overlap. Before publishing, compare the candidate SHA with the current main head and skip superseded candidates; this handles out-of-order scheduling without letting an old queued build regress latest. No path filter: every main push triggers the workflow as requested.

## Risks / Trade-offs

- Smaller runtimes can omit required shared libraries or standard-library modules → inspect dependencies and exercise the actual final image before publication.
- Bind-mount ownership differs between Linux and Docker Desktop → document UID/GID mapping and permission preparation; test default and overridden identities.
- Container paths differ from host paths → make the path mapping explicit in examples and report documentation.
- GHCR permissions or package-name collisions can block publishing → use repository-linked packages and GITHUB_TOKEN, surface actionable job errors, and verify the first main publication.
- GHCR package visibility may default to private → document how maintainers enable public visibility if desired; do not change visibility automatically.
- The size ceiling may need future revision as runtime dependencies evolve → fail CI on regressions rather than silently relaxing the agreed budget.

## Migration Plan

Add the image distribution alongside native installation. After implementation lands on main, verify both tags and the digest through GHCR and pull/run the published image. Users can pin the SHA tag or digest; rollback uses an earlier image. The native CLI and existing output records remain compatible.

## References

- https://hub.docker.com/_/python
- https://docs.docker.com/docker-hub/image-library/trusted-content/
- https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
