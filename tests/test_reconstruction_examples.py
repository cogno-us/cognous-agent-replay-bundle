from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agent_replay_bundle.importers import ImportContractError, _sha256, import_bounded_workflow
from agent_replay_bundle.reconstruction import ReconstructionBundle


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
PUBLISHED = (
    "bounded_success_reconstruction_v0_2.json",
    "bounded_lost_ack_reconstruction_v0_2.json",
)


def _load(name: str) -> ReconstructionBundle:
    return ReconstructionBundle.model_validate_json(
        (EXAMPLES / name).read_text(encoding="utf-8")
    )


def _retained_importer_inputs(bundle: ReconstructionBundle):
    by_type: dict[str, list[dict]] = {}
    for record in sorted(bundle.records, key=lambda item: item.source_sequence):
        by_type.setdefault(record.record_type, []).append(copy.deepcopy(record.data))

    proposal = by_type["runtime_proposal"][0]
    cp = {
        "run_id": bundle.run_id,
        "decisions": by_type.get("runtime_decision", []),
        "attempts": by_type.get("control_plane_attempt_transition", []),
        "observations": by_type.get("effect_observation", []),
        "reconciliations": by_type.get("reconciliation", []),
    }
    moltbot = {
        "execution_envelope": by_type["execution_envelope"][0],
        "execution_result": by_type["execution_result"][0],
        "attempts": by_type.get("destination_attempt", []),
        "attempt_events": by_type.get("destination_attempt_event", []),
        "effects": by_type.get("destination_effect", []),
    }
    return cp, proposal, moltbot


def _assert_claimed_commitments(bundle: ReconstructionBundle, proposal: dict, moltbot: dict):
    decision = next(r for r in bundle.records if r.record_type == "runtime_decision")
    binding = decision.data["binding"]
    operation = moltbot["execution_envelope"]["operation"]
    destination = moltbot["effects"][0]

    assert binding["proposal_commitment"] == _sha256(proposal)
    assert operation["proposal_commitment"] == binding["proposal_commitment"]
    assert proposal["payload_commitment"] == _sha256(proposal["payload"])
    assert binding["payload_commitment"] == proposal["payload_commitment"]
    assert operation["payload_commitment"] == proposal["payload_commitment"]

    operation_digest = _sha256(operation)
    assert destination["operation_digest"] == operation_digest
    assert all(
        item.verification_status == "checked_match"
        for item in bundle.commitments
        if item.label in {"payload_commitment", "effect_id", "operation_digest"}
    )


def _assert_operation_and_destination_binding(proposal: dict, moltbot: dict):
    operation = moltbot["execution_envelope"]["operation"]
    destination = moltbot["effects"][0]
    for field in (
        "actor", "principal", "manifest_id", "manifest_version", "manifest_digest",
        "action_id", "adapter_id", "target", "payload", "payload_commitment",
        "requested_permissions", "amount", "unit", "effects", "requirement_id",
    ):
        assert operation[field] == proposal[field]
    assert destination["grant_id"] == operation["grant_id"]
    assert destination["target"] == operation["target"]
    assert destination["amount"] == operation["amount"]
    assert destination["unit"] == operation["unit"]
    assert json.loads(destination["payload_json"]) == operation["payload"]


def test_reconstruction_examples_validate_semantically_through_hardened_importer():
    for name in PUBLISHED:
        bundle = _load(name)
        assert bundle.bundle_version == "0.2.0"
        assert bundle.semantics.external_effect_execution is False
        assert bundle.semantics.independent_effect_verification is False
        assert bundle.metadata["fixture_provenance"] == "generated_from_actual_pinned_producer_run"

        cp, proposal, moltbot = _retained_importer_inputs(bundle)
        reconstructed = import_bounded_workflow(
            cp, proposal=proposal, moltbot_export=moltbot
        )
        assert reconstructed.status == "reconstruction_complete"
        _assert_operation_and_destination_binding(proposal, moltbot)
        _assert_claimed_commitments(bundle, proposal, moltbot)


def test_lost_ack_example_keeps_unknown_and_later_applied_state():
    bundle = _load("bounded_lost_ack_reconstruction_v0_2.json")
    transitions = [
        record.data["status"]
        for record in bundle.records
        if record.record_type == "control_plane_attempt_transition"
    ]
    observations = [
        record.data["state"]
        for record in bundle.records
        if record.record_type == "effect_observation"
    ]
    result = next(r.data for r in bundle.records if r.record_type == "execution_result")
    assert transitions[-1] == "unknown"
    assert observations[-1] == "applied"
    assert result["status"] == "unknown"
    assert result["acknowledged"] is False


@pytest.mark.parametrize("tamper", ["actor", "destination_amount"])
def test_published_example_tampering_fails_semantic_validation(tamper: str):
    bundle = _load("bounded_success_reconstruction_v0_2.json")
    cp, proposal, moltbot = _retained_importer_inputs(bundle)

    if tamper == "actor":
        proposal["actor"] = "urn:attacker"
    else:
        moltbot["effects"][0]["amount"] = 999999

    with pytest.raises(ImportContractError):
        import_bounded_workflow(cp, proposal=proposal, moltbot_export=moltbot)
