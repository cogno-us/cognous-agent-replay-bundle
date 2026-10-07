# Merged producer compatibility

## Scope

Starting Replay revision: `440e32df8f5b083a955c5369f85a85d3e231808e`.

This change admits exactly one additional pair for the existing bounded producer 2.0.0 export:

- Control Plane `d3dadee70bd319812b207389ab1e0f6efe511916`.
- Execution Runtime `c3c3ee7188b9367cf70b08074b9c40a5c70c94ac`.

Historical producer pairs and their metadata remain unchanged. The new executor revision cannot be paired with an older Control Plane, nor the new Control Plane with the old executor. Unknown revisions remain rejected. No producer claims are relabeled as another source revision.

## Qualification

The existing generator checks actual Git heads and executes 14 real synthetic producer scenarios through public bounded execution/export interfaces. It verifies destination database and Control Plane record bytes remain unchanged by import. The new explicit qualification suite covers all 14 scenarios plus five unsupported-pair/contradiction cases: **19 passed locally**.

The dedicated Linux CI job requires all checkout inputs, retains generated source and result artifacts, and limits its test batch to two minutes. Existing historical/persistence qualification remains in the repository's Python 3.11/3.12 CI. No new optional skipped tests are introduced into that default suite.

## Boundaries

This qualifies the existing bounded export format produced by newer code. It does not import atomic claim consumption, grant budget transactions or refund-intent ownership evidence as new record types. Those require explicitly versioned exports and their own consumer mappings. It does not combine the mutually exclusive runtime profiles, adopt the non-authorizing decision-input sidecar, reauthorize, perform effects, reevaluate policy, establish external truth or advance hub pins.

Hub PR #21 accepted the separate 73-test atomic-profile qualification at merge `b717bf232058dae613c3ad2038e7dde6500fc758`. That result does not substitute for this consumer qualification. Downstream Evidence Pack, ODES and GAX must accept their own exact compatibility generation before default hub adoption.
