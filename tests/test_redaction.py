"""Tests for the redaction module."""

import pytest

from agent_replay_bundle.models import (
    ActionProposal,
    ActionType,
    AgentReplayBundle,
    AuthorityRecord,
    BlockedAction,
    BundleStatus,
    DecisionResult,
    PolicyDecision,
    PolicyEvaluationTrace,
    PolicyRuleEvaluation,
    RelianceRecord,
    RunFrame,
    SignatureMetadata,
    TraceRuleResult,
)
from agent_replay_bundle.redaction import redact_replay_bundle


def make_full_bundle():
    frame = RunFrame(
        frame_id="frame-001",
        task="Test task",
        actor="test-agent",
        environment="test",
        allowed_tools=["tool_a"],
        blocked_tools=["tool_b"],
        policy_version="v1.0",
        created_at="2026-01-01T00:00:00Z",
    )
    ap = ActionProposal(
        action_id="action-001",
        run_id="run-001",
        tool_name="tool_a",
        action_type=ActionType.read,
        target="res://original-target",
        payload={"key": "sensitive_value", "count": 5},
        proposed_at="2026-01-01T00:00:01Z",
        reason="Original reason.",
    )
    pd = PolicyDecision(
        decision_id="decision-001",
        action_id="action-001",
        run_id="run-001",
        result=DecisionResult.allow,
        policy_name="pol-v1",
        reason="Original decision reason.",
        decided_at="2026-01-01T00:00:02Z",
        deterministic_fingerprint="fp-001",
        trace_id="trace-001",
    )
    trace = PolicyEvaluationTrace(
        trace_id="trace-001",
        run_id="run-001",
        action_id="action-001",
        evaluated_at="2026-01-01T00:00:02Z",
        rules_evaluated=[
            PolicyRuleEvaluation(
                rule_name="rule-1",
                matched=True,
                result=TraceRuleResult.allow,
                reason="Rule reason.",
            )
        ],
        final_result=DecisionResult.allow,
        deterministic_fingerprint="fp-001",
    )
    ba = BlockedAction(
        blocked_id="blocked-001",
        action_id="action-001",
        run_id="run-001",
        reason="Blocked reason.",
        policy_name="pol-v1",
        blocked_at="2026-01-01T00:00:03Z",
    )
    return AgentReplayBundle(
        bundle_id="bundle-001",
        run_id="run-001",
        generated_at="2026-01-01T00:00:00Z",
        frame=frame,
        action_proposals=[ap],
        policy_decisions=[pd],
        policy_traces=[trace],
        blocked_actions=[ba],
        final_output="Original final output.",
    )


class TestRedactionDeepCopy:
    def test_returns_new_object(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted is not bundle

    def test_original_unchanged(self):
        bundle = make_full_bundle()
        _ = redact_replay_bundle(bundle)
        assert bundle.action_proposals[0].payload == {"key": "sensitive_value", "count": 5}
        assert bundle.action_proposals[0].target == "res://original-target"
        assert bundle.final_output == "Original final output."
        assert bundle.status == BundleStatus.complete


class TestPayloadRedaction:
    def test_payloads_redacted_by_default(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.action_proposals[0].payload == {"redacted": True}

    def test_payload_field_in_redacted_fields(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        fields = redacted.redaction_metadata.redacted_fields
        assert "action_proposals[0].payload" in fields


class TestTargetRedaction:
    def test_targets_not_redacted_by_default(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.action_proposals[0].target == "res://original-target"

    def test_targets_redacted_when_requested(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_targets=True)
        assert redacted.action_proposals[0].target == "[REDACTED]"
        assert "action_proposals[0].target" in redacted.redaction_metadata.redacted_fields


class TestFinalOutputRedaction:
    def test_final_output_not_redacted_by_default(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.final_output == "Original final output."

    def test_final_output_redacted_when_requested(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_final_output=True)
        assert redacted.final_output == "[REDACTED]"
        assert "final_output" in redacted.redaction_metadata.redacted_fields


class TestReasonRedaction:
    def test_reasons_not_redacted_by_default(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.action_proposals[0].reason == "Original reason."

    def test_reasons_redacted_when_requested(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_reasons=True)
        assert redacted.action_proposals[0].reason == "[REDACTED]"
        assert redacted.policy_decisions[0].reason == "[REDACTED]"
        assert redacted.policy_traces[0].rules_evaluated[0].reason == "[REDACTED]"
        assert redacted.blocked_actions[0].reason == "[REDACTED]"


class TestPreservation:
    def test_ids_preserved(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_payloads=True, redact_targets=True)
        assert redacted.bundle_id == bundle.bundle_id
        assert redacted.run_id == bundle.run_id
        assert redacted.action_proposals[0].action_id == "action-001"
        assert redacted.policy_decisions[0].decision_id == "decision-001"

    def test_fingerprints_preserved(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.policy_decisions[0].deterministic_fingerprint == "fp-001"
        assert redacted.policy_traces[0].deterministic_fingerprint == "fp-001"

    def test_decision_results_preserved(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_reasons=True)
        assert redacted.policy_decisions[0].result == DecisionResult.allow

    def test_trace_relationships_preserved(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.policy_decisions[0].trace_id == "trace-001"
        assert redacted.policy_traces[0].trace_id == "trace-001"


class TestRedactionMetadata:
    def test_status_set_to_redacted(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle)
        assert redacted.status == BundleStatus.redacted

    def test_redaction_metadata_populated(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redaction_policy="test-policy")
        assert redacted.redaction_metadata is not None
        assert redacted.redaction_metadata.redacted is True
        assert redacted.redaction_metadata.redacted_at is not None
        assert redacted.redaction_metadata.redaction_policy == "test-policy"

    def test_custom_replacement(self):
        bundle = make_full_bundle()
        redacted = redact_replay_bundle(bundle, redact_targets=True, replacement="***")
        assert redacted.action_proposals[0].target == "***"
        assert redacted.redaction_metadata.replacement == "***"
