# Worker 9 — Control Plane persistence compatibility

## Scope and starting point

Started from accepted Replay main
`274543f1cd7171784a923a8e37015017a0d8bc9d`.
The only open Replay PR observed at start was PR #5, an older executor-profile
workstream; it was not consumed.

Before editing, producer-v2 selected only Control Plane
`2ea9528eeb87e14ff10f05de06473122b9df540f`. Passing
`248d899634d9db3518e831bc7ab568a48733f825` reached the explicit
`unsupported Control Plane revision` gate in `import_bounded_workflow`.
No shape-based fallback exists.

## Compatibility decision

Accepted executor producer 2.0.0 remains
`177354e959cc78c59c1a776f018cfbfbf28c927b` with Execution Envelope 0.2.0.

Replay now recognizes two exact Control Plane revisions for that same producer-v2
wire contract:

- `2ea9528eeb87e14ff10f05de06473122b9df540f` — existing accepted observation repair;
- `248d899634d9db3518e831bc7ab568a48733f825` — accepted record-store persistence repair.

The Control Plane compare is two commits ahead and changes bounded-record
persistence mechanics plus tests/docs: interprocess locking, transaction reload,
unique temporary replacement, file/directory fsync and fail-closed filesystem
requirements. The consumed `BoundedRunRecord`, decision, attempt, observation
and reconciliation wire models are unchanged. Reconstruction Bundle therefore
remains 0.2.0.

Each Control Plane revision receives its own exact revision-pinned producer
profile. The executor profile remains producer 2.0.0. Unknown revisions and
unsupported executor/Control Plane combinations still fail closed.

## Preserved semantics

The adapter continues to preserve producer 1.0.0 and historical unversioned
mappings, distinct Control Plane/executor attempt namespaces, null and rejected
observations, rejected historical evidence, `observed_absent` with
`retry_eligible=false`, recovered applied state without rewriting prior
acknowledgement history, and source-asserted provenance without independent
assurance promotion.

No historical artifact, example, or repository revision string was globally
relabeled.

## Qualification

The focused qualification runs actual producer output using:

- Control Plane `248d899634d9db3518e831bc7ab568a48733f825`;
- Moltbot Safe `177354e959cc78c59c1a776f018cfbfbf28c927b`;
- the existing pinned Manifest fixture.

It reuses the accepted producer-v2 generator and covers ordinary success, lost
acknowledgement, restart recovery, prior observed absence with retry disabled,
rejected observation followed by accepted applied recovery, partial delivery,
denied no-effect, attempt-namespace separation, exact unsupported-revision
rejection, and contradictory effect/observation/attempt evidence rejection.
The generator also exercises its complete 14-scenario producer-v2 matrix.

For each generated scenario, Replay import must leave the Control Plane record
bytes and logical destination database unchanged. Replay remains non-effecting
and does not reevaluate policy or independently verify delivery.

CI is configured to run the focused persistence qualification before the complete
Replay suite and example checks on Python 3.11 and 3.12. Executed totals and the
one-time exact-head CI observation are recorded in the PR handoff when available.

## Migration implications

No Reconstruction Bundle migration or format-version bump is required. Consumers
that intentionally pin accepted producer-v2 Control Plane revisions may add
`248d899634d9db3518e831bc7ab568a48733f825`; consumers that require the older
revision may continue using `2ea9528eeb87e14ff10f05de06473122b9df540f`.
Revision selection remains explicit and does not authenticate repository origin.

No ODES, Evidence Pack, GAX, executor or hub change is included here.


## PR #9 correction — reviewed head `1afcc0c40ceceddcaee50c7ee714404f4e918347`

CI run `37580255993` exposed two focused qualification defects: an
over-strong historical-rejection assertion and tuple metadata that was not JSON
stable. The first corrected run also exposed that the selected persistence
revision was reset to the earlier compatibility default when the producer
contract was rebuilt later in import.

Corrections:
- Rejected-recovery qualification now asserts the actual retained Control Plane
  reconciliation sequence, rejected observation/reasons, and later accepted
  applied observation in producer order. It compares executor-side rejected
  observation records only to evidence actually present in
  `moltbot_export.rejected_observations`; no record is manufactured or duplicated.
- `compatible_control_plane_revisions` is emitted as a JSON-native list.
- The validated producer contract is retained through import. Its
  `control_plane_revision` is the actual selected revision, while
  `compatible_control_plane_revisions` remains the supported set.
- Tests cover both accepted v2 Control Plane revisions and require agreement
  among top-level metadata, the Control Plane producer profile and the nested
  producer contract.
- Exact bundle JSON round-trip equality remains required.

Validation at head `25c4bff8674a11378893c889fd5b68733432fc81`,
GitHub Actions run `37580648145`:
- Python 3.11 focused persistence qualification: **18 passed**.
- Python 3.11 complete Replay suite: **231 passed**.
- Python 3.11 existing example checks: **passed**.
- Python 3.12 focused persistence qualification: **18 passed**.
- Python 3.12 complete Replay suite: **231 passed**.
- Python 3.12 producer-v2 example generation: **14 real-producer scenarios passed**;
  destination and Control Plane stores remained unchanged by Replay import.
- Python 3.12 existing example checks: **passed**.
- Workflow conclusion: **success**.

No format-version bump, downstream change or self-merge was made.
