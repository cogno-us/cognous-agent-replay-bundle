# Batch 4C-B Replay checkpoint

2026-10-06 UTC. Executor-only Batch 4C-A is accepted; this batch changes only
Replay. Review branch: `worker14b/replay-producer-v2`. No self-merge.
Starting main: `f63ce914504dd06813c4ccd199b0570dbd8dd427`, matching the previously
accepted Replay baseline. Final head and one-time CI result are recorded in the
PR description. Concurrent main is rechecked before publication.

Entry point: this checkpoint. [Compatibility and migration](../reconstruction_import.md#producer-200-migration-batch-4c-b).
[Machine-readable scenario results](producer_v2_results.json).
[Generated examples](../../examples/producer-v2/).

## Compatibility decision

Keep Reconstruction Bundle 0.2.0: existing source records preserve the complete
new JSON semantics. Add explicit executor producer 2.0.0 mapping at
`177354e959cc78c59c1a776f018cfbfbf28c927b`, paired only with Control Plane
`2ea9528eeb87e14ff10f05de06473122b9df540f`. Manifest remains
`46c950bed37fe3812000895430bc0312d29e37ce`.
Historical 1.0.0 and unversioned mappings and examples retain their original
revisions. CI checks out both generations; separate subprocess execution avoids
mixing producer modules. No adjacent repository or hub lock changed.

## Executed qualification

The generator verifies actual checkout SHAs, uses accepted synthetic test setup
with explicit ObservationPolicy and clock, and exercises public execution,
producer export, Replay import and model validation. It compares the full logical
SQLite dump (all tables), destination content/count and CP record bytes before
and after import. SQLite physical page bytes are not the invariant: read-connection
lifecycle can checkpoint WAL pages without changing logical records.

| Scenario | Destination before / after import | Result retained |
|---|---|---|
| Ordinary execution | 1 applied / 1 applied | Acknowledged, accepted observation |
| Wrong-effect, stale, malformed, contradictory post-dispatch observation (4 cases) | 1 applied / 1 applied each | Acknowledged and newly executed; observation null; rejected content and reasons retained |
| Unavailable post-dispatch observation | 1 applied / 1 applied | Acknowledged; null observation and unavailability reason |
| Restart recovery after unavailable observation | 1 applied / 1 applied | Same original effect, CP reconciliation attempt and original executor attempt |
| Lost acknowledgement | 1 applied / 1 applied | Unknown attempt delivery status; accepted applied observation remains separate |
| Partial delivery | 1 partial / 1 partial | Partial original effect retained |
| Prior attempt then fresh absence | 0 / 0 | Observed absence, retry false; resubmission denied |
| Missing-policy denial | 0 / 0 | No effect, rejection reasons |
| Historical applied observation | 1 applied / 1 applied | Raw local evidence, no CP validation claim |
| Historical absent observation | 0 / 0 | Historical absence, no dispatch permission |

All 13 are required safety invariants and passed. Recorded identities, exact
payload/amount/unit/target/grant/state and per-example bundle digests are in the
results file. Import created no additional effect or authority decision. Restart
means reopening the same-host durable stores, not cross-process or distributed
qualification. No live confinement, institutional authentication or independently
verified delivery is claimed.

Adversarial tests cover unsupported version/revision pairs, enclosing identity
changes, dangling/conflicting attempts, missing owning CP records, copied or
substituted reconciliations, accepted/rejected promotion, state contradictions,
retry claims, destination payload/target/amount/state substitution, absent effect
evidence, invalid accepted timestamps/policy and conflicting terminal attempts.
Existing operation-binding, immutable-ID, namespace, legacy and 1.0.0 tests remain.

## Validation commands

Set `ARB_PINNED_CONTROL_PLANE_ROOT` and `ARB_PINNED_MOLTBOT_ROOT` to the historical
CI pins; set `ARB_V2_CONTROL_PLANE_ROOT` and `ARB_V2_MOLTBOT_ROOT` to the accepted
repaired revisions above. Set `ARB_PINNED_MANIFEST_FIXTURE` to the pinned Manifest
checkout's `examples/refund_integration_v1_1.manifest.json`.

```sh
PYTHONPATH=src pytest -q
PYTHONPATH=src python scripts/generate_reconstruction_examples.py --output-dir generated-historical
PYTHONPATH=src python scripts/generate_producer_v2_examples.py --output-dir generated-v2
PYTHONPATH=src python -m agent_replay_bundle.cli check-examples
python -m compileall -q src scripts
```

Local validation on Python 3.12.14 / pytest 9.1.1 / pydantic 2.13.5:
**204 passed, zero failures, zero skips**, including 43 new tests (13 outcome
cases, 29 adversarial cases and one published-example consistency check).
The generator separately passed all 13 scenarios; every logical database and CP
record remained unchanged across import. Historical example generation, CLI
example checks, compilation and diff whitespace checks passed. Python 3.11 is
covered by configured CI but was not run locally. CI is
checked once after submission, with the exact head and returned run IDs/status
recorded in the PR. No queued-run polling or unexecuted green claim.

## Remaining bounded work

Governor review and final-head CI disposition. ODES, Evidence Pack and Alvorada/GAX
must separately consume producer 2.0.0 and these preserved Replay record kinds,
without flattening rejected evidence or inventing missing attribution. Original
Replay identity and canonical-digest agreement must survive downstream packaging.
Hub PR #4 pin updates, release rerun and Batch 4C cases 3–5 remain separate pending
work. No downstream compatibility or hub release pass is established here.
