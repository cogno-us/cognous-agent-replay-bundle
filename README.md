# Agent Replay Bundle

**Portable replay records for AI-agent runs.**

Agent Replay Bundle is a public schema and reference validator for packaging AI-agent runs into portable evidence artifacts. A replay bundle records the task frame, action proposals, policy decisions, policy evaluation traces, blocked actions, authority records, reliance records, final output, validation report, redaction metadata, and signature metadata.

It is designed for teams that need to reconstruct what an AI agent proposed, what policy decided, what was blocked, what authority existed, what sources were relied on, and how the run can be inspected later.

This repository is intentionally narrow. It is not an agent framework, not a model runtime, not a replay viewer, not a hosted service, and not a complete enterprise governance platform. It is a reference format for replayable AI-agent run evidence.

---

## What it is

Agent Replay Bundle defines a portable, JSON-based evidence package for completed or partially completed AI-agent runs. It provides:

- A **JSON Schema** for the replay bundle format
- **Pydantic models** for working with bundles in Python
- A **semantic validator** that checks bundle consistency beyond schema compliance
- A **redaction helper** that strips sensitive fields while preserving governance-relevant structure
- An **export integrity signing** helper using HMAC-SHA256
- A **CLI** (`arb`) for validation, summarization, redaction, signing, and verification
- **Five example bundles** covering real-world agent scenarios

---

## Why it matters

Agent teams need to reconstruct:

- What was the task?
- What actions did the agent propose?
- What policy decisions occurred?
- What was blocked?
- What authority existed?
- What sources were relied on?
- What output was produced?
- Was the export redacted?
- Was the export signed?
- Is the bundle internally consistent?

This repo gives teams a portable evidence format for AI-agent run review.

---

## What a replay bundle contains

| Section | Description |
|---|---|
| **bundle metadata** | bundle_id, run_id, status, producer, timestamps |
| **run frame** | task, actor, environment, allowed/blocked tools, policy version |
| **action proposals** | every action the agent proposed, with tool, type, target, payload |
| **policy decisions** | allow/block/escalate decisions for each action |
| **policy evaluation traces** | per-rule evaluation detail for each decision |
| **blocked actions** | explicit records of blocked actions |
| **authority records** | authority grants in scope for the run |
| **reliance records** | data sources the agent relied upon |
| **final output** | the agent's final response or result |
| **validation report** | embedded semantic validation results |
| **redaction metadata** | what was redacted, when, and under what policy |
| **signature metadata** | export integrity signature |

---

## Quickstart

```bash
pip install -e ".[dev]"
pytest
arb validate examples/customer_service_replay_bundle.json
arb summarize examples/customer_service_replay_bundle.json
arb redact examples/customer_service_replay_bundle.json --out /tmp/redacted.json --targets --final-output
arb sign examples/customer_service_replay_bundle.json --secret "demo-secret" --out /tmp/signed.json
arb verify /tmp/signed.json --secret "demo-secret"
```

---

## Example bundle

```json
{
  "bundle_id": "bundle-cs-001",
  "bundle_version": "0.1",
  "run_id": "run-cs-001",
  "status": "complete",
  "generated_at": "2026-07-01T10:15:00Z",
  "frame": {
    "frame_id": "frame-cs-001",
    "task": "Retrieve customer order history and send a follow-up email.",
    "actor": "customer-service-agent",
    "environment": "production",
    "allowed_tools": ["crm_read", "email_compose"],
    "blocked_tools": ["bulk_email_send"],
    "policy_version": "cs-policy-v3.1",
    "created_at": "2026-07-01T10:14:55Z"
  },
  "action_proposals": ["..."],
  "policy_decisions": ["..."],
  "blocked_actions": ["..."],
  "final_output": "Return confirmed. Email blocked: no external_send authority."
}
```

See `examples/` for complete example bundles.

---

## CLI

```
arb validate path/to/replay_bundle.json
arb summarize path/to/replay_bundle.json
arb redact path/to/replay_bundle.json --out path/to/redacted.json [--targets] [--final-output] [--reasons] [--policy "policy-name"]
arb sign path/to/replay_bundle.json --secret SECRET --out path/to/signed.json [--key-id KEY_ID]
arb verify path/to/signed_replay_bundle.json --secret SECRET
arb check-examples
```

Exit codes:
- `0` — success or valid
- `1` — invalid (validate/verify)
- `2` — usage, file not found, or parse error

---

## Validation

`arb validate` runs semantic validation beyond JSON schema checking. It verifies:

- All IDs are non-empty
- All cross-references between proposals, decisions, traces, and blocked actions are consistent
- Fingerprints match between decisions and their traces
- Signature metadata is complete if `signed=true`
- Redaction metadata is complete if `redacted=true`

Warnings are informational and do not affect the `valid` status.

See [docs/validation.md](docs/validation.md) for the full rule set.

---

## Redaction

```python
from agent_replay_bundle.redaction import redact_replay_bundle

redacted = redact_replay_bundle(
    bundle,
    redact_payloads=True,
    redact_targets=True,
    redact_final_output=True,
    redaction_policy="public-review",
)
```

Redaction:
- Returns a deep copy; does not mutate the original
- Preserves all IDs, timestamps, decision results, policy names, fingerprints, and cross-references
- Records redacted field paths in `redaction_metadata.redacted_fields`

See [docs/redaction.md](docs/redaction.md).

---

## Signing

```python
from agent_replay_bundle.signing import sign_replay_bundle, verify_signed_replay_bundle

signed = sign_replay_bundle(bundle, secret="my-secret", key_id="key-001")
is_valid = verify_signed_replay_bundle(signed, secret="my-secret")
```

Signing uses HMAC-SHA256 with a caller-supplied secret. This is export integrity — not production key management. See [docs/signing.md](docs/signing.md) for details and limitations.

For signed exports, `SignedReplayBundle.signature_metadata` is the authoritative signature metadata. `AgentReplayBundle.signature_metadata` is optional embedded metadata for systems that store signature state directly on the bundle.

---

## Relationship to Agent Control Plane

Agent Control Plane records and governs agent action proposals at runtime.
Agent Replay Bundle defines a portable evidence format for packaging those run records for audit, review, redaction, signing, validation, and replay.

Agent Control Plane can emit replay bundles, but this format can also be used by other systems.

---

## JSON schemas

Schemas are in `schemas/`. Primary schema: `schemas/agent_replay_bundle.schema.json`.

All schemas use JSON Schema Draft 2020-12.

---

## Examples

| File | Scenario |
|---|---|
| `customer_service_replay_bundle.json` | CRM read allowed, email blocked |
| `internal_research_replay_bundle.json` | Document search and export escalation |
| `procurement_replay_bundle.json` | Vendor comparison, PO blocked for approval |
| `redacted_replay_bundle.json` | Customer service bundle with payloads and output redacted |
| `signed_replay_bundle.json` | Structurally valid signed bundle with demo signature |

---

## Security / scope

See [SECURITY.md](SECURITY.md).

This is a schema, validator, redaction helper, and signing helper. It is not a security boundary. It does not enforce runtime access control. HMAC signing is export integrity, not production key management. Redaction must be configured correctly.

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

---

## License

Apache-2.0. See LICENSE and NOTICE.
