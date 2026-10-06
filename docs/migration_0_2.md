# Migration to reconstruction bundle 0.2.0

The existing `AgentReplayBundle` 0.1 format and CLI remain available for
legacy bundles. Version 0.2.0 adds a separate `ReconstructionBundle` API
rather than silently changing 0.1 field semantics.

## Why a separate model

The legacy bundle was designed around a frame, proposals, policy decisions and
run summaries. The bounded authorization-to-effect workflow adds decision
bindings, stable effects, lifecycle attempt records, observations,
reconciliations and executor-side evidence. Forcing these records into legacy
fields would lose producer semantics or invent fields that did not exist.

## Migration paths

### Legacy Control Plane ReplayBundle

Use:

```python
from agent_replay_bundle import import_legacy_control_plane_replay

reconstruction = import_legacy_control_plane_replay(source_dict)
```

The importer is pinned to Control Plane commit
`283500652d47a692fb0b99a1172a6d5faffbd9a7` because the legacy producer does
not embed a format version.

### Bounded workflow

Use:

```python
from agent_replay_bundle import import_bounded_workflow

reconstruction = import_bounded_workflow(
    bounded_run_record,
    proposal=runtime_proposal,
    moltbot_export=executor_export,
)
```

The proposal or executor export may be omitted; omission is visible in the
machine-readable import report and the reconstruction will not claim that the
missing evidence exists.

## Status change

Do not map legacy `status="complete"` to effect completion.

0.2 reconstruction status is one of:

- `reconstruction_complete` — the declared import inputs were represented;
- `reconstruction_partial` — dependencies or semantics remain missing or
  unresolved;
- `incomplete` — construction has not established a complete import; or
- `redacted` — this is a derivative with explicit redaction lineage.

These labels describe reconstruction, not real-world delivery or verification.

## Redaction/signing change

The legacy helper remains unchanged for compatibility. For 0.2 reconstruction
exports, use `redact_reconstruction_bundle` and
`sign_reconstruction_bundle`.

A 0.2 redacted derivative always has a new bundle ID and fresh integrity
metadata. Legacy behavior must not be assumed to authenticate a modified 0.2
derivative.

## Unsupported producer revisions

A different producer commit or an unknown Execution Envelope version requires a
new or reviewed adapter profile. Do not bypass the check by changing a version
string or relying on similar fields.


## Integrity compatibility note

HMAC exports produced before the cross-record validation hardening excluded the
entire `integrity` array from the MAC input. Current HMAC verification binds
the integrity metadata and blanks only the HMAC value itself. Older
reconstruction HMACs therefore require explicit legacy handling outside the
current verifier or must be re-signed from trusted source content.

A `key_id` in current metadata is an authenticated caller-supplied label, not
proof of key identity or custody. Redacted derivatives still discard source
integrity metadata, receive a new bundle identity and must be signed again if
shared-secret authentication is required.


## Executor producer profile 1.0.0

New executor evidence may declare
`urn:cognous:profiles:moltbot-safe-executor-evidence:1.0.0`. The importer
requires the exact profile/schema/envelope versions, the reviewed producer
revision, and consistent decision/effect/operation bindings.

The embedded repository revision is a **source-asserted provenance claim**.
Import does not turn it into independently established provenance. A pinned CI
checkout can establish compatibility separately, but that fact is not written
back into the producer artifact.

Historical executor exports with no `producer_profile` remain supported under
the prior revision-pinned adapter for
`6b0ba1185bcd390f71df947dda349415e4105f5f`. They are not relabeled as
profile 1.0.0 and retain `moltbot_legacy_unversioned=true` in reconstruction
metadata.
