# Reconstruction import contract 0.2.0

## Scope

The 0.2.0 reconstruction API imports recorded producer evidence. It does **not**:

- rerun a model;
- reevaluate policy unless a caller performs that separately;
- renew an authorization;
- repeat an effect;
- convert a producer acknowledgement into destination verification; or
- convert synthetic local destination state into independently verified institutional delivery.

The importer's default semantics are therefore non-effecting.

## Supported producer profiles

| Profile | Producer | Version basis |
|---|---|---|
| `control-plane-legacy-replay@28350065` | `ReplayBundle` from Cognous Agent Control Plane | no embedded format version; pinned to commit `283500652d47a692fb0b99a1172a6d5faffbd9a7` |
| `control-plane-bounded-run@28350065` | `BoundedRunRecord` from Cognous Agent Control Plane | no embedded format version; pinned to the same commit |
| `moltbot-safe-envelope-0.2.0@6b0ba118` | Execution Envelope 0.2.0 plus SQLite effects, attempts and append-only attempt events | explicit envelope version plus pinned commit `6b0ba1185bcd390f71df947dda349415e4105f5f` |

The bounded adapter is also tested with Manifest v1.1 at
`46c950bed37fe3812000895430bc0312d29e37ce` and Alvorada Authority Context
0.1.0 at `fb3d97938969a89e149e8ff8db2756091d1233fc`.

Shape similarity is never treated as a version negotiation mechanism.

## Confirmed legacy mapping

The pinned legacy Control Plane serializer emits these producer names:

| Producer field | 0.2 reconstruction representation |
|---|---|
| `replay_bundle_id` | `metadata.source_bundle_id` |
| `actions[]` | ordered `SourceRecord(record_type="action_proposal")` |
| `decisions[]` | ordered `SourceRecord(record_type="policy_decision")` |
| `policy_traces[]` | ordered policy-trace records |
| `authority_records[]` | ordered authority records |
| `reliance_records[]` | ordered reliance records |
| `blocked_actions[]` | ordered blocked-action records |

The importer preserves producer field names inside each source record instead of
renaming record content and pretending the original commitment covered the
renamed form.

## Bounded-workflow mapping

The bounded producer is event-oriented:

- each `RuntimeDecision` is retained as an immutable source record;
- each occurrence in `attempts[]` is retained in source order as an attempt
  lifecycle transition;
- observations and reconciliations are retained independently;
- proposal `correlation_id`, manifest identifiers, decision/effect IDs,
  grant/revision, policy versions, requirement commitment and role-mapping
  version/digest are retained where supplied;
- blocked/held decisions retain their producer `reasons`.

A Control Plane attempt ID and Moltbot Safe attempt ID are different namespaces.
A link is created only when producer evidence explicitly supplies the Moltbot
attempt ID, such as the pinned adapter acknowledgement. Shared decision/effect
identifiers can support lineage but do not establish attempt identity.

## Authority Context identifiers

Two different values are intentionally retained:

1. the proposal's `authority_context_ref`, which is a **profile reference**;
2. the Control Plane authorization binding's `authority_context_id`, which is
   a **resolved context-instance identifier**.

At the pinned Moltbot adapter revision, its
`ExecutionOperation.authority_context_id` field carries the proposal profile
reference. The reconstruction representation labels that value as
`authority_context_profile_ref` to avoid silently converting it into the
Control Plane context-instance identifier.

The Control Plane `AuthorizationBinding` does not persist
`institution_id` or `authority_domain`. Moltbot Safe derives those values
from its trusted integration context. Reconstruction preserves that provenance;
it does not backfill the Control Plane record from caller assertions.

## Import report and value states

Each adapter emits an `ImportReport` containing:

- explicit field mappings;
- unmapped fields;
- missing dependencies;
- unsupported semantics;
- conversion warnings;
- redactions; and
- value-state findings.

When applicable, values are classified as `absent`, `unknown`,
`unavailable`, or `redacted`.

`reconstruction_complete` means the declared import contract was completely
represented. It does **not** mean an external effect was completed or
independently verified. `reconstruction_partial` means source dependencies or
semantics remain unresolved. Partial/unknown destination states remain visible.

## Commitment handling

The importer records the source commitment value, algorithm and canonicalization
profile. It independently checks only contracts it actually knows at the pinned
revision, including:

- proposal payload commitment;
- Moltbot execution-envelope payload commitment; and
- Control Plane effect identity from proposal commitment + grant ID + grant
  revision.

The bounded importer validates the supplied evidence as one cross-record chain:
the full RuntimeProposal commitment must equal the decision binding; applicable
proposal fields must equal the binding; the Execution Envelope operation must
equal the proposal and grant/effect-limit binding; and durable destination rows
must equal the committed operation for grant, target, amount, unit and decoded
payload. A copied operation digest is insufficient when the row content differs.

Execution-result attempt IDs are namespace-aware. Ordinary destination
execution resolves to a Moltbot attempt row. The pinned reconciliation path may
return a Control Plane attempt ID when no new destination attempt is created.
Dangling IDs and incompatible namespace/status combinations are rejected; the
two namespaces are never treated as identity-equivalent.

This adapter accepts one supplied RuntimeProposal/Execution Envelope operation.
Multiple authorization bindings are rejected rather than forced onto that
proposal. Missing optional evidence can make reconstruction explicitly partial;
contradictory supplied evidence is a contract error.

Other source-provided digests are retained as attributed producer claims unless
a documented verification profile checks them. A digest is never recomputed
over renamed or redacted content and represented as the original digest.

Conflicting content under an immutable decision, attempt or effect identity is
rejected. Embedded execution-result observations and Control Plane
reconciliations are checked against their enclosing effect/state contracts.

## Integrity and redaction

Reconstruction HMAC uses HMAC-SHA256 over canonical reconstruction content plus
its integrity metadata, with only the HMAC signature value blanked to avoid a
circular input. The authenticated metadata therefore includes HMAC kind,
algorithm, canonicalization profile, subject bundle ID, caller-supplied
`key_id` label and verification claim. Verification also requires the declared
subject to equal the actual bundle ID and the algorithm/profile to match the
implemented profile.

A verifier must possess the same shared secret. This provides shared-secret
export integrity; it is not a publicly verifiable issuer signature and does not
establish production key custody. `key_id` is merely an authenticated label
provided by the caller; the HMAC does not independently authenticate the
identity or custody of that key.

Redaction order is:

1. copy the source reconstruction;
2. assign a new bundle identity;
3. record `redacted_derivative -> source_bundle_id`;
4. modify the selected source records;
5. remove source integrity metadata;
6. downgrade affected original commitment checks to attributed claims; and
7. compute fresh integrity metadata for the derivative.

A stale HMAC or source digest is never presented as authenticating modified
content.

## Evidence classes

Source records default to `producer_reported`. Tests and downstream tooling
may label separately produced evidence as `locally_generated` or
`independently_checked`, but the importer does not manufacture either label.
Synthetic Moltbot SQLite observation is producer/local destination evidence, not
independent institutional verification.
