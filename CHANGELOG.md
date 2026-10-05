# Changelog

## Unreleased

- Hardened bounded import with proposal -> decision -> envelope -> destination cross-record validation.
- Added namespace-aware execution-result attempt resolution and embedded observation/reconciliation checks.
- Rejects multiple authorization bindings in the single-proposal importer instead of forcing a match.
- HMAC now authenticates integrity metadata except the signature value itself; legacy HMACs require explicit handling or re-signing.
- Added Governor regression coverage for proposal, destination, attempt, envelope and HMAC metadata substitution.


## 0.2.0 - 2026-10-05

- Added revision-pinned legacy and bounded Control Plane import profiles.
- Added Moltbot Safe Execution Envelope 0.2.0 / SQLite evidence import.
- Added ordered lifecycle preservation for repeated attempt records.
- Added explicit lineage, commitment metadata and machine-readable loss reports.
- Added reconstruction-only semantics that do not renew authorization or create effects.
- Added conflict checks for immutable decision, attempt and effect identities.
- Added reconstruction HMAC documentation and redacted-derivative identity semantics.
- Added pinned Control Plane -> Moltbot Safe integration tests.

The 0.1 `AgentReplayBundle` API remains available for compatibility.
