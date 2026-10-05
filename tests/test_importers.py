from __future__ import annotations

import copy

import pytest

from agent_replay_bundle.importers import (
    ImportContractError,
    import_bounded_workflow,
    import_legacy_control_plane_replay,
)
from agent_replay_bundle.reconstruction import (
    redact_reconstruction_bundle,
    sign_reconstruction_bundle,
    verify_reconstruction_hmac,
)


def legacy_source():
    return {
        "replay_bundle_id": "legacy-bundle-1",
        "run_id": "run-1",
        "generated_at": "2026-10-05T00:00:00Z",
        "frame": {
            "frame_id": "frame-1",
            "task": "synthetic",
            "actor": "agent",
            "environment": "test",
            "allowed_tools": [],
            "blocked_tools": [],
            "policy_version": "v1",
            "created_at": "2026-10-05T00:00:00Z",
        },
        "actions": [{
            "action_id": "a1", "run_id": "run-1", "tool_name": "t",
            "action_type": "write", "target": "x", "payload": {},
            "proposed_at": "2026-10-05T00:00:01Z", "reason": None,
        }],
        "decisions": [{
            "decision_id": "d1", "action_id": "a1", "run_id": "run-1",
            "result": "allow", "policy_name": "p", "reason": "ok",
            "decided_at": "2026-10-05T00:00:02Z",
            "deterministic_fingerprint": "fp", "trace_id": None,
        }],
        "policy_traces": [],
        "authority_records": [],
        "reliance_records": [],
        "blocked_actions": [],
        "final_output": None,
    }


def _binding():
    return {
        "proposal_commitment": "sha256:" + "1" * 64,
        "manifest_id": "m1",
        "manifest_version": "1.1",
        "manifest_digest": "sha256:" + "2" * 64,
        "actor": "actor",
        "principal": "principal",
        "action_id": "refund.issue",
        "adapter_id": "adapter",
        "target": "target",
        "payload_commitment": "sha256:" + "3" * 64,
        "requested_permissions": ["refund.issue"],
        "amount": 50.0,
        "unit": "USD",
        "effects": 1,
        "authority_context_id": "urn:context:instance",
        "authority_context_version": "0.1.0",
        "authority_context_status": "proposed_pending_governor_review",
        "requirement_id": "req-1",
        "requirement_commitment": "sha256:" + "4" * 64,
        "grant_id": "grant-1",
        "grant_revision": "1",
        "policy_versions": [{"ref": "policy", "version": "1"}],
        "role_mapping_version": "roles-v1",
        "role_mapping_digest": "sha256:" + "5" * 64,
        "effective_max_effects": 1,
    }


def _effect_id(binding):
    from agent_replay_bundle.importers import _sha256

    return _sha256({
        "proposal": binding["proposal_commitment"],
        "grant_id": binding["grant_id"],
        "grant_revision": binding["grant_revision"],
    })


def bounded_source():
    binding = _binding()
    effect_id = _effect_id(binding)
    return {
        "run_id": "run-1",
        "decisions": [{
            "decision_id": "decision-1",
            "effect_id": effect_id,
            "result": "authorized",
            "reasons": [],
            "decided_at": "2026-10-05T00:00:00Z",
            "binding": binding,
        }],
        "attempts": [
            {
                "attempt_id": "cp-attempt-1",
                "effect_id": effect_id,
                "decision_id": "decision-1",
                "started_at": "2026-10-05T00:00:01Z",
                "status": "attempted",
                "acknowledgement": {},
                "error": None,
            },
            {
                "attempt_id": "cp-attempt-1",
                "effect_id": effect_id,
                "decision_id": "decision-1",
                "started_at": "2026-10-05T00:00:01Z",
                "status": "unknown",
                "acknowledgement": {},
                "error": "ack lost",
            },
        ],
        "observations": [{
            "effect_id": effect_id,
            "observed_at": "2026-10-05T00:00:02Z",
            "state": "applied",
            "destination_state": {"effect_id": effect_id},
        }],
        "reconciliations": [],
    }


def proposal_source():
    from agent_replay_bundle.importers import _sha256

    payload = {"customer_id": "c1"}
    return {
        "manifest_id": "m1",
        "manifest_version": "1.1",
        "manifest_digest": "sha256:" + "2" * 64,
        "actor": "actor",
        "principal": "principal",
        "action_id": "refund.issue",
        "adapter_id": "adapter",
        "target": "target",
        "payload": payload,
        "payload_commitment": _sha256(payload),
        "requested_permissions": ["refund.issue"],
        "amount": 50.0,
        "unit": "USD",
        "effects": 1,
        "authority_context_ref": "urn:profile:0.1.0",
        "requirement_id": "req-1",
        "correlation_id": "corr-1",
        "run_id": "run-1",
        "evidence_refs": ["evidence-1"],
    }


def moltbot_source(cp):
    from agent_replay_bundle.importers import _sha256

    effect_id = cp["decisions"][0]["effect_id"]
    payload = {"customer_id": "c1"}
    op = {
        "actor": "actor",
        "principal": "principal",
        "institution_id": "institution",
        "authority_domain": "customer-refunds",
        "manifest_id": "m1",
        "manifest_version": "1.1",
        "manifest_digest": "sha256:" + "2" * 64,
        "proposal_commitment": "sha256:" + "1" * 64,
        "action_id": "refund.issue",
        "adapter_id": "adapter",
        "target": "target",
        "payload": payload,
        "payload_commitment": _sha256(payload),
        "requested_permissions": ["refund.issue"],
        "amount": 50.0,
        "unit": "USD",
        "effects": 1,
        "authority_context_id": "urn:profile:0.1.0",
        "requirement_id": "req-1",
        "grant_id": "grant-1",
        "grant_revision": "1",
        "effective_max_effects": 1,
    }
    operation_digest = _sha256(op)
    return {
        "execution_envelope": {
            "version": "0.2.0",
            "decision_id": "decision-1",
            "effect_id": effect_id,
            "operation": op,
            "attempt_id": None,
        },
        "execution_result": {
            "status": "unknown",
            "decision_id": "decision-1",
            "effect_id": effect_id,
            "attempt_id": "molt-attempt-1",
            "attempted": True,
            "acknowledged": False,
            "observed_state": "applied",
            "newly_executed": True,
            "observation": {"effect_id": effect_id, "state": "applied"},
            "error": "ack lost",
        },
        "attempts": [{
            "attempt_id": "molt-attempt-1",
            "effect_id": effect_id,
            "decision_id": "decision-1",
            "operation_digest": operation_digest,
            "created_at": 1.0,
        }],
        "attempt_events": [
            {"event_id": 1, "attempt_id": "molt-attempt-1", "status": "attempted", "error": None, "created_at": 1.0},
            {"event_id": 2, "attempt_id": "molt-attempt-1", "status": "unknown", "error": "ack lost", "created_at": 2.0},
        ],
        "effects": [{
            "effect_id": effect_id,
            "operation_digest": operation_digest,
            "grant_id": "grant-1",
            "target": "target",
            "amount": 50.0,
            "unit": "USD",
            "payload_json": '{"customer_id":"c1"}',
            "state": "applied",
        }],
    }


def test_confirmed_legacy_mappings_are_explicit():
    bundle = import_legacy_control_plane_replay(legacy_source())
    report = bundle.import_reports[0]
    assert bundle.metadata["source_bundle_id"] == "legacy-bundle-1"
    assert report.field_mappings["actions"] == "records[action_proposal]"
    assert report.field_mappings["decisions"] == "records[policy_decision]"
    assert any(r.record_type == "action_proposal" for r in bundle.records)
    assert any(r.record_type == "policy_decision" for r in bundle.records)


def test_bounded_lifecycle_transitions_are_not_collapsed():
    bundle = import_bounded_workflow(bounded_source(), proposal=proposal_source())
    transitions = [r for r in bundle.records if r.record_type == "control_plane_attempt_transition"]
    assert [r.data["status"] for r in transitions] == ["attempted", "unknown"]
    assert transitions[0].identifiers["attempt_id"] == transitions[1].identifiers["attempt_id"]
    assert bundle.semantics.external_effect_execution is False


def test_unknown_ack_followed_by_applied_observation_is_preserved():
    bundle = import_bounded_workflow(bounded_source(), proposal=proposal_source())
    statuses = [r.data["status"] for r in bundle.records if r.record_type == "control_plane_attempt_transition"]
    observations = [r.data["state"] for r in bundle.records if r.record_type == "effect_observation"]
    assert statuses[-1] == "unknown"
    assert observations[-1] == "applied"


def test_separate_attempt_namespaces_are_not_equated_without_explicit_link():
    cp = bounded_source()
    bundle = import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=moltbot_source(cp))
    assert bundle.links == []
    finding = next(f for f in bundle.import_reports[0].findings if f.code == "M002")
    assert finding.value_state == "unknown"


def test_explicit_executor_attempt_link_is_preserved_without_identity_equivalence():
    cp = bounded_source()
    cp["attempts"][-1]["acknowledgement"] = {"attempt_id": "molt-attempt-1"}
    bundle = import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=moltbot_source(cp))
    assert len(bundle.links) == 1
    assert bundle.links[0].link_type == "explicit"
    assert bundle.links[0].establishes_identity_equivalence is False


def test_conflicting_immutable_attempt_content_is_rejected():
    cp = bounded_source()
    cp["attempts"][1]["decision_id"] = "different"
    with pytest.raises(ImportContractError, match="conflicting content"):
        import_bounded_workflow(cp, proposal=proposal_source())


def test_conflicting_immutable_effect_content_is_rejected():
    cp = bounded_source()
    m = moltbot_source(cp)
    second = copy.deepcopy(m["effects"][0])
    second["target"] = "different"
    m["effects"].append(second)
    with pytest.raises(ImportContractError, match="conflicting content"):
        import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=m)


def test_dangling_control_plane_decision_reference_is_rejected():
    cp = bounded_source()
    cp["attempts"][0]["decision_id"] = "missing"
    with pytest.raises(ImportContractError, match="dangling decision_id"):
        import_bounded_workflow(cp, proposal=proposal_source())


def test_dangling_control_plane_effect_reference_is_rejected():
    cp = bounded_source()
    cp["observations"][0]["effect_id"] = "missing"
    with pytest.raises(ImportContractError, match="dangling effect_id"):
        import_bounded_workflow(cp, proposal=proposal_source())


def test_dangling_moltbot_attempt_event_is_rejected():
    cp = bounded_source()
    m = moltbot_source(cp)
    m["attempt_events"][0]["attempt_id"] = "missing"
    with pytest.raises(ImportContractError, match="dangling"):
        import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=m)


def test_moltbot_operation_digest_tamper_is_rejected():
    cp = bounded_source()
    m = moltbot_source(cp)
    m["effects"][0]["operation_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ImportContractError, match="operation_digest mismatch"):
        import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=m)


def test_moltbot_identifier_mismatch_is_rejected():
    cp = bounded_source()
    m = moltbot_source(cp)
    m["execution_result"]["effect_id"] = "wrong"
    with pytest.raises(ImportContractError, match="identifiers"):
        import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=m)


def test_unsupported_executor_version_is_rejected():
    cp = bounded_source()
    m = moltbot_source(cp)
    m["execution_envelope"]["version"] = "9.9.9"
    with pytest.raises(ImportContractError, match="unsupported"):
        import_bounded_workflow(cp, proposal=proposal_source(), moltbot_export=m)


def test_effect_identity_tamper_is_rejected():
    cp = bounded_source()
    cp["decisions"][0]["effect_id"] = "sha256:" + "0" * 64
    with pytest.raises(ImportContractError, match="effect identity"):
        import_bounded_workflow(cp, proposal=proposal_source())


def test_payload_commitment_tamper_is_rejected():
    p = proposal_source()
    p["payload"]["customer_id"] = "tampered"
    with pytest.raises(ImportContractError, match="payload commitment"):
        import_bounded_workflow(bounded_source(), proposal=p)


def test_hmac_detects_tamper_and_is_shared_secret_only():
    bundle = import_bounded_workflow(bounded_source(), proposal=proposal_source())
    signed = sign_reconstruction_bundle(bundle, "secret", key_id="test-key")
    assert verify_reconstruction_hmac(signed, "secret") is True
    assert verify_reconstruction_hmac(signed, "wrong") is False
    signed.records[0].data["actor"] = "tampered"
    assert verify_reconstruction_hmac(signed, "secret") is False
    hmac_metadata = next(i for i in signed.integrity if i.kind == "hmac")
    assert "shared secret" in hmac_metadata.verification_claim


def test_redaction_creates_new_derivative_identity_and_drops_stale_hmac():
    bundle = import_bounded_workflow(bounded_source(), proposal=proposal_source())
    signed = sign_reconstruction_bundle(bundle, "secret")
    target = next(r.source_path for r in signed.records if r.record_type == "runtime_proposal")
    redacted = redact_reconstruction_bundle(signed, redact_paths={target})
    assert redacted.bundle_id != signed.bundle_id
    assert redacted.derivation.source_bundle_id == signed.bundle_id
    assert redacted.status == "redacted"
    assert all(i.kind != "hmac" for i in redacted.integrity)
    assert any(i.kind == "content-digest" for i in redacted.integrity)
    assert verify_reconstruction_hmac(redacted, "secret") is False
    assert any(f.value_state == "redacted" for f in redacted.import_reports[0].findings)
