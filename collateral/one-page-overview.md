# Agent Replay Bundle — One-Page Overview

## Purpose

A portable reconstruction format, importer, validator and CLI for agent-run evidence. Reconstruction Bundle 0.2.0 imports exact supported producer revisions while keeping legacy bundle formats and historical provenance distinct.

## Problem

Logs from authority evaluation, execution and recovery can disagree or omit important facts. Review requires a connected record of proposals, decisions, attempts, observations and source lineage, including uncertainty rather than a retrospective success story.

## What It Provides

- **Producer imports:** Validate exact supported Control Plane and executor combinations; reject unknown revisions rather than guessing compatibility from shape.
- **Identity continuity:** Preserve proposal, decision and effect identity while keeping Control Plane and executor attempt namespaces separate.
- **Recovery history:** Retain unknown acknowledgement, rejected/null observations and evidence-only recovery lineage.
- **Loss and completeness:** Represent declared reconstruction coverage and missing information without claiming effect completion.

## Where It Fits

After a bounded refund attempt, the importer consumes the actual Control Plane and executor records. It preserves whether the destination was observed applied, absent, partial or unresolved, and which source supplied each fact. An Evidence Pack or ODES exporter can then derive review material without rerunning the action or rewriting the original records.

A valid signature, chain inclusion, message receipt, reasoning instruction or evidence-package digest does not authorize execution. Institutional authority must be supplied and evaluated through the appropriate trusted boundary.

## Evidence and Limits

The [accepted hub lock](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/component-lock.json) selects this component at `043830b56595cecddfa65c064afd1c0b95e64792`. Read the component's [README](../README.md) for version-specific acceptance and the [hub support ledger](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md) for the executed scope. Component acceptance is not automatic adoption of newer revisions or production qualification.

Reconstruction is non-effecting. It does not reevaluate policy, renew authorization, repeat an effect or independently verify delivery. Reconstruction completeness is not destination finality. A valid digest or HMAC is not institutional authority; redaction and key custody require deployment-specific controls.

## Practical Next Step

Choose one bounded example and follow the [README](../README.md). Compare expected and observed results and retain uncertainty. The [business collateral](business-collateral.md) supplies evaluation questions and the component's wider context.

[Cognous](https://cogno.us) · [Source](https://github.com/cogno-us/cognous-replay-bundle) · [All stack components](https://github.com/cogno-us/cognous-open-control-stack). Existing licenses and notices apply.
