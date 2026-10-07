"""Qualification of producer-v2 against the accepted Control Plane persistence repair."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_replay_bundle import ReconstructionBundle, import_bounded_workflow
from agent_replay_bundle.importers import (
    CONTROL_PLANE_V2_PERSISTENCE_REVISION,
    ImportContractError,
)


@pytest.fixture(scope="module")
def persistence_cases(tmp_path_factory):
    cp_root = os.environ.get("ARB_V2_PERSISTENCE_CONTROL_PLANE_ROOT")
    executor_root = os.environ.get("ARB_V2_MOLTBOT_ROOT")
    if not cp_root or not executor_root:
        pytest.skip("accepted persistence-repair producer checkouts not configured")
    output = tmp_path_factory.mktemp("producer-v2-persistence")
    env = os.environ.copy()
    env["ARB_V2_CONTROL_PLANE_ROOT"] = cp_root
    subprocess.run(
        [sys.executable, "scripts/generate_producer_v2_examples.py", "--output-dir", str(output)],
        check=True,
        env=env,
    )
    return {
        "sources": json.loads((output / "producer_v2_sources.json").read_text()),
        "results": json.loads((output / "producer_v2_results.json").read_text()),
    }


def test_persistence_revision_is_exact_and_wire_compatible(persistence_cases):
    results = persistence_cases["results"]
    assert results["pins"]["control_plane"] == CONTROL_PLANE_V2_PERSISTENCE_REVISION
    assert results["pins"]["executor"] == "177354e959cc78c59c1a776f018cfbfbf28c927b"
    assert len(results["scenarios"]) == 14
    assert all(v["records_unchanged"] for v in results["scenarios"].values())


@pytest.mark.parametrize(
    "name",
    [
        "success",
        "lost_ack",
        "restart",
        "prior_absence",
        "rejected_restart",
        "partial",
        "denied",
    ],
)
def test_required_persistence_repair_scenarios_import_without_mutation(persistence_cases, name):
    source = persistence_cases["sources"][name]
    before = copy.deepcopy(source)
    bundle = import_bounded_workflow(**source)
    assert source == before
    assert bundle.bundle_version == "0.2.0"
    assert bundle.metadata["control_plane_revision"] == CONTROL_PLANE_V2_PERSISTENCE_REVISION
    assert not bundle.semantics.external_effect_execution
    assert not bundle.semantics.policy_reevaluation
    assert not bundle.semantics.independent_effect_verification

    summary = persistence_cases["results"]["scenarios"][name]
    assert summary["effect_count_before_import"] == summary["effect_count_after_import"]
    assert summary["records_unchanged"]

    history = next(iter(bundle.metadata["effect_observation_history"].values()))
    if name == "lost_ack":
        assert history["latest_supported_destination_state"] == "applied"
        assert history["acknowledgement_history"][-1]["status"] == "unknown"
        assert history["acknowledgement_history"][-1]["acknowledgement"] == {}
    elif name in {"restart", "rejected_restart"}:
        assert history["latest_supported_destination_state"] == "applied"
        assert history["latest_accepted_observation"]["observation"]["state"] == "applied"
    elif name == "prior_absence":
        assert history["latest_supported_destination_state"] == "absent"
        assert history["retry_eligible"] is False
        assert summary["effect_count_after_import"] == 0
    elif name == "partial":
        assert history["latest_supported_destination_state"] == "partial"
    elif name == "denied":
        assert summary["effect_count_after_import"] == 0


def test_rejected_observation_then_applied_recovery_keeps_rejection(persistence_cases):
    source = persistence_cases["sources"]["rejected_restart"]
    bundle = import_bounded_workflow(**source)
    retained = [r.data for r in bundle.records if r.record_type == "reconciliation"]
    assert any(not r["observation_accepted"] for r in retained)
    assert retained[-1]["observation_accepted"] is True
    assert retained[-1]["observation"]["state"] == "applied"
    rejected = [r for r in bundle.records if r.record_type == "rejected_executor_observation"]
    assert rejected
    history = next(iter(bundle.metadata["effect_observation_history"].values()))
    assert history["latest_supported_destination_state"] == "applied"


def test_attempt_namespaces_remain_separate(persistence_cases):
    source = persistence_cases["sources"]["restart"]
    export = source["moltbot_export"]
    executor_ids = {row["attempt_id"] for row in export["attempts"]}
    control_plane_ids = {row["attempt_id"] for row in export["control_plane_attempts"]}
    assert executor_ids
    assert control_plane_ids
    assert executor_ids.isdisjoint(control_plane_ids)
    assert export["attempt_identity"]["namespace"] == "control_plane"


@pytest.mark.parametrize(
    "mutation",
    ["unsupported_revision", "contradictory_effect", "contradictory_observation", "contradictory_attempt"],
)
def test_persistence_revision_still_fails_closed_on_contract_contradictions(persistence_cases, mutation):
    source = copy.deepcopy(persistence_cases["sources"]["success"])
    if mutation == "unsupported_revision":
        source["control_plane_revision"] = "248d899634d9db3518e831bc7ab568a48733f824"
    elif mutation == "contradictory_effect":
        source["moltbot_export"]["effects"][0]["effect_id"] = "other-effect"
    elif mutation == "contradictory_observation":
        source["control_plane_record"]["reconciliations"][-1]["observation"]["effect_id"] = "other-effect"
    else:
        source["moltbot_export"]["execution_result"]["attempt_id"] = "other-attempt"
        source["moltbot_export"]["attempt_identity"]["attempt_id"] = "other-attempt"
    with pytest.raises(ImportContractError):
        import_bounded_workflow(**source)


def test_source_asserted_provenance_is_not_promoted(persistence_cases):
    source = persistence_cases["sources"]["success"]
    bundle = import_bounded_workflow(**source)
    contract = bundle.metadata["moltbot_producer_contract"]
    assert contract["provenance"]["mode"] == "versioned_profile"
    assert contract["provenance"]["source_asserted"] == source["moltbot_export"]["provenance"]["source_asserted"]
    assert contract["provenance"]["independently_established"] == source["moltbot_export"]["provenance"]["independently_established"]
    assert all(r.evidence_class == "producer_reported" for r in bundle.records)


def test_persistence_revision_bundle_round_trips(persistence_cases):
    source = persistence_cases["sources"]["success"]
    bundle = import_bounded_workflow(**source)
    assert ReconstructionBundle.model_validate_json(bundle.model_dump_json()) == bundle
