# Agent Replay Bundle — Business Collateral

## 1. Executive Summary

A portable reconstruction format, importer, validator and CLI for agent-run evidence. Reconstruction Bundle 0.2.0 imports exact supported producer revisions while keeping legacy bundle formats and historical provenance distinct.

## 2. The Business Problem

Logs from authority evaluation, execution and recovery can disagree or omit important facts. Review requires a connected record of proposals, decisions, attempts, observations and source lineage, including uncertainty rather than a retrospective success story.

## 3. The Component in One View

| Capability | Practical role |
|---|---|
| Producer imports | Validate exact supported Control Plane and executor combinations; reject unknown revisions rather than guessing compatibility from shape. |
| Identity continuity | Preserve proposal, decision and effect identity while keeping Control Plane and executor attempt namespaces separate. |
| Recovery history | Retain unknown acknowledgement, rejected/null observations and evidence-only recovery lineage. |
| Loss and completeness | Represent declared reconstruction coverage and missing information without claiming effect completion. |
| Portable review | Validate, summarize, redact and sign exports; HMAC export integrity is separate from production key management. |

## 4. Who Should Evaluate It

Engineers can inspect the reference contracts and examples; enterprise architecture, security and governance reviewers can examine the boundary and evidence. Evaluate this component for its named responsibility rather than as a complete governance platform.

## 5. A Bounded Workflow

After a bounded refund attempt, the importer consumes the actual Control Plane and executor records. It preserves whether the destination was observed applied, absent, partial or unresolved, and which source supplied each fact. An Evidence Pack or ODES exporter can then derive review material without rerunning the action or rewriting the original records.

This is a reference use case. Adopting the format or running the example does not establish a production deployment, institutional acceptance or measured business benefit.

## 6. Relationship to the Stack

This component contributes **reconstruct what the retained records support**. The [Cognous Open Control Stack](https://github.com/cogno-us/cognous-open-control-stack) connects declared proposals, independent authority, constrained execution and retained review evidence. Components remain separately owned and versioned; the [selected lock](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/component-lock.json) determines which revisions participate in the supported integration.

A valid signature, chain inclusion, message receipt, reasoning instruction or evidence-package digest does not authorize execution. Institutional authority must be supplied and evaluated through the appropriate trusted boundary.

## 7. What the Evidence Supports

The hub selects `043830b56595cecddfa65c064afd1c0b95e64792`. Producer profile 2.0.0 supports the exact older observation-repair and newer persistence-repair Control Plane revisions documented in the [compatibility checkpoint](../docs/workstreams/replay-control-plane-persistence-checkpoint.md). Legacy unversioned and profile-1.0.0 mappings remain separate. Reconstruction Bundle stays 0.2.0.

The [accepted hub evidence](https://github.com/cogno-us/cognous-open-control-stack/blob/5737267d94d2b445735c95e8480a31de73a2abe8/examples/control-plane-store-adoption/qualification-summary.json) supports bounded synthetic integration at its exact pins. Aggregate test totals do not establish deployment benefit, compliance or independent real-world verification. The [support ledger](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/release-status.md) distinguishes the standard reference, separate protected-worker campaign and unqualified production work.

## 8. What It Does Not Establish

Reconstruction is non-effecting. It does not reevaluate policy, renew authorization, repeat an effect or independently verify delivery. Reconstruction completeness is not destination finality. A valid digest or HMAC is not institutional authority; redaction and key custody require deployment-specific controls.

## 9. Evaluation Questions

- Which exact input, output and source revision will the receiving system consume?
- Who supplies trusted authority or evidence, and which assumptions remain outside this component?
- Can a reviewer trace the result to retained sources, including rejected or missing information?
- Which documented checks were actually executed in the intended environment?
- What deployment-specific work is required before relying on the result?

## 10. Why Open Reference Material Matters

Public formats, source, examples and evidence allow reviewers to inspect the claimed boundary and reproduce its checks. They also expose what has not been tested. Openness supports review; it does not substitute for independent assurance or operating responsibility.

## 11. Practical Next Step

Follow the [README](../README.md) and select one bounded use case. Inspect its inputs and expected outputs, reproduce the documented checks where prerequisites are available, and record failures and unresolved assumptions alongside passes. Use the [one-page overview](one-page-overview.md) for initial stakeholder orientation.

## 12. Status and Attribution

This collateral summarizes merged public material at repository `043830b56595cecddfa65c064afd1c0b95e64792` and the accepted hub baseline `5737267d94d2b445735c95e8480a31de73a2abe8`. It does not anticipate pending branches. The protected-worker result applies only to its recorded Linux/bubblewrap fixture; live OpenShell and logical-intent prevention are not hub-supported at this snapshot.

[Cognous](https://cogno.us) · [Source repository](https://github.com/cogno-us/cognous-agent-replay-bundle) · [Stack responsibilities](https://github.com/cogno-us/cognous-open-control-stack/blob/main/docs/architecture.md). Existing licenses and third-party notices remain controlling.
