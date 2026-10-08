# W3 — Replay and Evidence compatibility checkpoint

## Baseline

Prepared against W0 hub `6ad8f6a409d3140aa65af19d5c850dd8e58f8a7d`, Replay main
`d758db92e5d7b1109a001d92077036d80cc87a19`, and Evidence Pack main
`97316b9170e4bef8310612a2f5823795a097c81d`.

The hub-selected historical consumer chain remains Reconstruction Bundle `0.2.0`
at Replay `459e4ba62fca49364aebb0050cd5fb2dd5a71bfa` and Evidence Pack schema
`0.2.0` with transformation
`agep-manifest-reconstruction-import/0.3.2` at
`b4baccd823d2a73be276c1de745b19cf7c56a0d6`.

## Exact compatibility matrix

The machine-readable matrix is
`qualification/w3/producer-consumer-compatibility.json`. It records only exact
revision/profile combinations already supported by accepted consumer code.

Shape similarity is not compatibility. No Cartesian product of producer revisions
is implied.

## W1/W2 dependency gate

The W0 fixture `cognous-w0-c1-c8/1.0` contains contract expectations for tenant
binding, evaluation failure and stop handling, but it is not accepted W1/W2
producer output. Therefore this checkpoint does not introduce a new Replay
importer version or Evidence transformation.

Mappings are prepared for tenant, refusal, stop, effect observation, recovery and
optional adapter provenance. Each remains `prepared_not_supported` until actual
accepted producer bytes and the exact accepted producer revision are available.

## Evidence-state vocabulary

- **missing** — an expected evidence field or dependency is absent.
- **incomplete** — evidence exists, but required lineage or completeness is not
  established.
- **unsupported** — producer revision/profile/version is outside an accepted
  exact compatibility pair.
- **unknown** — the producer explicitly records an unresolved/unknown state. It
  must not be collapsed into missing evidence or successful completion.

Historical reconstruction retains operation, effect, attempt, observation,
reconciliation and provenance records at the assurance level supplied by the
producer generation. Historical artifacts never acquire tenant, refusal, stop or
adapter assurance by backfill.

## Non-authority invariant

Replay import, Evidence transformation, validation and rendering are
non-authorizing. Their output cannot create, renew or widen a grant; cannot make
an execution eligible; and cannot turn unknown, missing, incomplete or
unsupported evidence into completed delivery.

## Next gate

After W1 or W2 merges an accepted producer generation, W3 must capture the actual
bytes and revision first, add a positive reconstruction fixture and negative
lineage fixtures, then decide whether the existing consumer versions can decode
the generation truthfully or whether a new importer/transformation version is
required.
