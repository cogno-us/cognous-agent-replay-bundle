# Executor producer profile migration

Replay accepts two executor producer forms.

## Versioned producer profile

New executor exports use:

- profile ID: `urn:cognous:profiles:moltbot-safe-executor-producer`
- profile version: `1.0.0`
- Execution Envelope version: `0.2.0`

Replay validates the declared producer profile, the supported repository revision,
the source-asserted repository revision, the envelope/result identities, the
operation binding, effects, attempts, append-only attempt events and observations.

The interface/profile version and repository revision are separate fields.
Source-asserted provenance is preserved as source-asserted. An empty
`independently_established` list is not upgraded into an independent
verification claim.

## Legacy unversioned exports

Historical unversioned Moltbot exports remain accepted only by the explicit
revision-pinned legacy adapter for
`6b0ba1185bcd390f71df947dda349415e4105f5f`.

Replay does not add producer-profile 1.0.0 metadata to those historical records,
does not change their producer revision and does not relabel them as evidence
from a newer executor implementation.

Migration is therefore forward-only: newly produced evidence should use the
versioned producer profile; stored historical bundles remain historical.


## Accepted producer implementation

The supported versioned executor profile `1.0.0` is accepted only from:

`cogno-us/moltbot-safe@1d308faf664c504b6e310db3c7a310153ef7b067`

The prior feature head `054e92d12ccb0bc756ca6652f39fc13b51e05d9b`
is not treated as an interchangeable accepted revision. Historical versioned
test artifacts from that head are not relabeled as if they were emitted by the
accepted merge.

## Attempt namespace and lineage validation

Versioned producer exports must carry `attempt_identity`,
`control_plane_attempts` and `observations`.

Replay preserves two attempt namespaces:

- `executor`: owned by `cogno-us/moltbot-safe` and resolvable to retained
  destination attempt records.
- `control_plane`: owned by
  `cogno-us/cognous-agent-control-plane` and resolvable to an explicitly
  attributed Control Plane attempt.

A Control Plane attempt is accepted only when the complete producer-supplied
attempt object exactly matches the retained Control Plane run record for that
attempt ID, decision and effect. Matching labels or IDs alone do not establish
lineage.

Legitimate historical `absent` and `unknown` observations may contain no
effect row. Applied or partial observations require retained destination effect
evidence. Denied results cannot coexist with retained effect evidence.
