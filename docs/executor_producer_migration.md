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
