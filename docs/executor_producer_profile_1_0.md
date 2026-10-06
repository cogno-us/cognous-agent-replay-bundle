# Executor producer profile migration

Replay accepts two Moltbot executor input contracts.

## Legacy unversioned input

Legacy executor dictionaries without `producer_profile` and
`producer_profile_version` remain supported only under the historical
revision pin:

`6b0ba1185bcd390f71df947dda349415e4105f5f`

Replay does not add a producer-profile version to those historical artifacts
and does not relabel their provenance.

## Versioned producer input

The new contract is:

- profile: `cognous.moltbot-safe.executor`
- profile version: `1.0.0`
- proposed repository revision:
  `894e1c115cb91229c474a906c51ea9af7999e675`

The profile version describes the emitted record semantics. The repository
revision identifies the implementation that emitted the record. They are not
interchangeable.

The producer record must explicitly distinguish source-asserted provenance
from independently established provenance. Replay preserves that distinction
and never upgrades a source assertion to independent verification.

Unsupported profile versions, repository revisions, repository identity or
contradictory envelope/effect/attempt bindings fail import.
