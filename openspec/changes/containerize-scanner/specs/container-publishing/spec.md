# Spec Delta

## Purpose

Automatically validate and distribute the scanner container through GitHub Container Registry, with traceable image tags and controlled publishing permissions.

## ADDED Requirements

### Requirement: Publish validated main commits
Every push to main SHALL trigger a GitHub Actions container workflow. Publication SHALL occur only after the app unit tests, container smoke tests, non-root identity checks, and image-size gate pass for that commit. The published artifact SHALL be the same image validated by the workflow.

#### Scenario: Successful main push
- **WHEN** a commit is pushed to main, remains the current head, and all required validation succeeds
- **THEN** its tested image is published to GHCR

#### Scenario: Failed validation
- **WHEN** any required validation fails
- **THEN** the workflow fails without publishing that candidate or updating latest

### Requirement: Traceable image references
Images SHALL be published under ghcr.io/<lowercase-owner>/<lowercase-repository> with latest and sha-<full-commit-sha> tags. Published images SHALL identify their source repository and commit revision through OCI labels. Workflow output SHALL report the published reference and digest.

#### Scenario: Published references
- **WHEN** a validated main image is published
- **THEN** users can select the moving latest tag or its commit-specific tag and inspect source and revision labels

### Requirement: Isolated publishing permissions
Publishing SHALL authenticate with the workflow GITHUB_TOKEN using contents:read and packages:write permissions scoped to the publish job. Pull-request validation SHALL NOT publish, log into GHCR, or receive packages:write permissions. No personal access token SHALL be required by the workflow.

#### Scenario: Pull request validation
- **WHEN** a pull request triggers container checks, including a fork pull request
- **THEN** the image builds and is validated without a registry push or publishing credentials

### Requirement: Ordered latest updates
Concurrent main builds SHALL NOT allow an older commit to replace the latest tag after a newer commit has been published.

Superseded candidates SHALL be permitted to skip publication while retaining validation results.

#### Scenario: Overlapping pushes
- **WHEN** a second main push arrives before the first workflow completes
- **THEN** publishing is serialized or superseded so latest does not regress to the older commit
