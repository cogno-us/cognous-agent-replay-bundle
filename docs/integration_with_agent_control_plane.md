# Integration with Agent Control Plane

This document describes the conceptual relationship between Agent Replay Bundle and Agent Control Plane.

## Overview

Agent Replay Bundle is a portable evidence format. Agent Control Plane is a runtime system that governs AI-agent action proposals. The two are related but independent.

## Conceptual flow

```
Agent runtime
  → Agent Control Plane
    → Run Record
      → Agent Replay Bundle
        → Validation Report
          → Redacted or Signed Export
            → Governance Evidence Pack
```

At each step:

1. **Agent runtime** — The AI agent receives a task and begins generating action proposals.

2. **Agent Control Plane** — At runtime, each action proposal is evaluated against policy. The control plane records the proposal, the policy decision, the evaluation trace, and blocked actions.

3. **Run Record** — At the end of the run, the control plane produces an internal run record with all governance-relevant data.

4. **Agent Replay Bundle** — The run record is serialized as an Agent Replay Bundle: a portable, self-contained JSON document that captures the full governance record of the run.

5. **Validation Report** — The bundle can be validated semantically using `validate_replay_bundle()` to verify internal consistency.

6. **Redacted or Signed Export** — For external review, the bundle can be redacted to remove sensitive payload data, or signed for export integrity, or both.

7. **Governance Evidence Pack** — The final package can be stored in audit logs, attached to incident reports, shared with compliance teams, or used for run reconstruction.

## What this repository does NOT include

This repository is a public reference implementation. It does not include:

- The Agent Control Plane runtime
- Any proprietary policy evaluation engine
- Any hosted service or API
- Any agent framework
- Any model runtime

Agent Control Plane can emit replay bundles using this format, but this format can also be used by other systems independently.

## Adopting the format without Agent Control Plane

Any system that records AI-agent action proposals and policy decisions can emit replay bundles by following this schema. The format is intentionally framework-agnostic and does not require Agent Control Plane.

To integrate:

1. Assign stable IDs to each run, action proposal, decision, trace, and blocked action.
2. Serialize your governance record to match the `AgentReplayBundle` schema.
3. Use `load_replay_bundle_json()` to validate the structure.
4. Use `validate_replay_bundle()` to check semantic consistency.
5. Optionally redact or sign before exporting.
