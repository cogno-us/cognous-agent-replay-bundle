"""Tests for Pydantic models."""

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
    RedactionMetadata,
    RelianceRecord,
    RunFrame,
    SignatureMetadata,
    SignedReplayBundle,
    SourceType,
    TraceRuleResult,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)


def make_frame(**kwargs):
    defaults = {
        "frame_id": "frame-001",
        "task": "Test task",
        "actor": "test-agent",
        "environment": "test",
        "policy_version": "v1.0",
        "created_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(kwargs)
    return RunFrame(**defaults)


def make_minimal_bundle(**kwargs):
    defaults = {
        "bundle_id": "bundle-001",
        "run_id": "run-001",
        "generated_at": "2026-01-01T00:00:00Z",
        "frame": make_frame(),
    }
    defaults.update(kwargs)
    return AgentReplayBundle(**defaults)


class TestRunFrame:
    def test_valid_minimal(self):
        frame = make_frame()
        assert frame.frame_id == "frame-001"
        assert frame.allowed_tools == []
        assert frame.blocked_tools == []

    def test_defaults(self):
        frame = make_frame()
        assert frame.allowed_tools == []
        assert frame.blocked_tools == []


class TestActionProposal:
    def test_valid(self):
        ap = ActionProposal(
            action_id="action-001",
            run_id="run-001",
            tool_name="crm_read",
            action_type=ActionType.read,
            target="crm://customers/123",
            proposed_at="2026-01-01T00:00:01Z",
        )
        assert ap.action_id == "action-001"
        assert ap.action_type == ActionType.read
        assert ap.payload == {}
        assert ap.reason is None

    def test_enum_validation(self):
        with pytest.raises(Exception):
            ActionProposal(
                action_id="a",
                run_id="r",
                tool_name="t",
                action_type="invalid_type",
                target="t",
                proposed_at="2026-01-01T00:00:00Z",
            )


class TestPolicyDecision:
    def test_valid(self):
        pd = PolicyDecision(
            decision_id="decision-001",
            action_id="action-001",
            run_id="run-001",
            result=DecisionResult.allow,
            policy_name="test-policy",
            reason="Allowed by policy.",
            decided_at="2026-01-01T00:00:02Z",
            deterministic_fingerprint="fp-abc123",
        )
        assert pd.result == DecisionResult.allow
        assert pd.trace_id is None


class TestAgentReplayBundle:
    def test_valid_minimal_bundle(self):
        bundle = make_minimal_bundle()
        assert bundle.bundle_id == "bundle-001"
        assert bundle.bundle_version == "0.1"
        assert bundle.status == BundleStatus.complete
        assert bundle.action_proposals == []
        assert bundle.policy_decisions == []
        assert bundle.metadata == {}

    def test_valid_full_bundle(self):
        frame = make_frame()
        ap = ActionProposal(
            action_id="action-001",
            run_id="run-001",
            tool_name="tool_x",
            action_type=ActionType.read,
            target="res://x",
            proposed_at="2026-01-01T00:00:01Z",
            reason="Because.",
        )
        pd = PolicyDecision(
            decision_id="decision-001",
            action_id="action-001",
            run_id="run-001",
            result=DecisionResult.allow,
            policy_name="pol-v1",
            reason="Allowed.",
            decided_at="2026-01-01T00:00:02Z",
            deterministic_fingerprint="fp-001",
        )
        bundle = AgentReplayBundle(
            bundle_id="bundle-full-001",
            run_id="run-001",
            generated_at="2026-01-01T00:00:00Z",
            frame=frame,
            action_proposals=[ap],
            policy_decisions=[pd],
            final_output="Done.",
        )
        assert len(bundle.action_proposals) == 1
        assert len(bundle.policy_decisions) == 1
        assert bundle.final_output == "Done."

    def test_status_enum(self):
        bundle = make_minimal_bundle(status="redacted")
        assert bundle.status == BundleStatus.redacted

    def test_default_bundle_version(self):
        bundle = make_minimal_bundle()
        assert bundle.bundle_version == "0.1"


class TestEnums:
    def test_action_type_values(self):
        values = {e.value for e in ActionType}
        assert "read" in values
        assert "write" in values
        assert "external_send" in values

    def test_decision_result_values(self):
        assert DecisionResult.allow.value == "allow"
        assert DecisionResult.block.value == "block"
        assert DecisionResult.escalate.value == "escalate"

    def test_source_type_values(self):
        assert SourceType.file.value == "file"
        assert SourceType.api.value == "api"

    def test_trace_rule_result_values(self):
        assert TraceRuleResult.none.value == "none"


class TestSignedReplayBundle:
    def test_signed_bundle_loads(self):
        bundle = make_minimal_bundle()
        sig = SignatureMetadata(
            signed=True,
            signed_at="2026-01-01T01:00:00Z",
            signature_algorithm="HMAC-SHA256",
            signature="abc123def456",
        )
        signed = SignedReplayBundle(
            signed_bundle_id="signed-001",
            replay_bundle=bundle,
            signature_metadata=sig,
        )
        assert signed.signed_bundle_id == "signed-001"
        assert signed.signature_metadata.signed is True


class TestValidationModels:
    def test_validation_issue(self):
        issue = ValidationIssue(
            severity=ValidationSeverity.error,
            code="E001",
            message="bundle_id is empty.",
        )
        assert issue.path is None

    def test_validation_report(self):
        report = ValidationReport(valid=True, checked_id="bundle-001")
        assert report.valid is True
        assert report.issues == []
        assert report.checked_object_type == "AgentReplayBundle"


class TestRedactionMetadata:
    def test_defaults(self):
        rm = RedactionMetadata()
        assert rm.redacted is False
        assert rm.redacted_fields == []
        assert rm.replacement == "[REDACTED]"
