# Roadmap

This document outlines planned and potential future work for Agent Replay Bundle.

## Near-term

- **Conformance test suite** — A standalone set of test bundles covering valid and invalid cases for each validation rule, suitable for testing third-party implementations.

- **Replay bundle diffing** — A utility for comparing two bundles for the same run (e.g., original vs. redacted, or two versions of the same run record).

- **Manifest-to-replay linkage examples** — Example patterns for linking a replay bundle to a run manifest, task log, or agent trace.

- **Additional framework examples** — Example bundles and integration notes for popular agent frameworks.

- **Richer redaction profiles** — Named redaction profiles (e.g., "public-review", "internal-audit", "incident-report") with preset field selections.

- **Optional OpenTelemetry mapping** — A reference mapping from replay bundle fields to OpenTelemetry span attributes for teams using OTel for agent observability.

- **Sample governance evidence pack export** — A reference structure for bundling multiple replay bundles, validation reports, and metadata into a governance evidence pack.

## Long-term

- **Replay viewer** — A minimal read-only viewer for inspecting replay bundles without re-executing tools.

- **Hosted validation service** — A lightweight hosted endpoint for validating bundles against the schema and semantic rules.

- **Enterprise storage adapters** — Reference patterns for storing and retrieving replay bundles from S3, GCS, Azure Blob, and similar object stores.

- **Compliance export mappings** — Reference mappings from replay bundle fields to common compliance and audit report formats.

- **Formal schema versioning** — A versioning scheme for the replay bundle format with migration guidance.

## Out of scope

The following are intentionally out of scope for this repository:

- Agent framework implementation
- Model runtime
- Hosted dashboard or analytics platform
- Production policy engine
- Proprietary replay analytics
