from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

from agent_replay_bundle.importers import import_bounded_workflow


CP_REVISION = "283500652d47a692fb0b99a1172a6d5faffbd9a7"
MOLTBOT_REVISION = "6b0ba1185bcd390f71df947dda349415e4105f5f"
MANIFEST_REVISION = "46c950bed37fe3812000895430bc0312d29e37ce"
ALVORADA_REVISION = "fb3d97938969a89e149e8ff8db2756091d1233fc"


def _load_actual_pinned_moltbot_helpers():
    cp_root = os.environ.get("ARB_PINNED_CONTROL_PLANE_ROOT")
    molt_root = os.environ.get("ARB_PINNED_MOLTBOT_ROOT")
    manifest_path = os.environ.get("ARB_PINNED_MANIFEST_FIXTURE")
    if not cp_root or not molt_root or not manifest_path:
        pytest.skip("pinned producer checkouts are not configured")

    cp_root_path = Path(cp_root)
    molt_root_path = Path(molt_root)
    if not cp_root_path.exists() or not molt_root_path.exists():
        pytest.skip("pinned producer checkout paths do not exist")

    sys.path.insert(0, str(cp_root_path / "src"))
    sys.path.insert(0, str(molt_root_path))
    os.environ["MOLTBOT_SAFE_CONTROL_PLANE_ROOT"] = str(cp_root_path)
    os.environ["MOLTBOT_SAFE_MANIFEST_FIXTURE"] = manifest_path

    helper_path = molt_root_path / "tests" / "test_safe_executor.py"
    spec = importlib.util.spec_from_file_location("arb_pinned_moltbot_helpers", helper_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sqlite_rows(path: Path, table: str) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]


def _export_sources(workflow, proposal, request, result, destination):
    cp_record = workflow.records.load().model_dump(mode="json")
    moltbot = {
        "execution_envelope": dataclasses.asdict(request),
        "execution_result": dataclasses.asdict(result),
        "effects": _sqlite_rows(destination.path, "effects"),
        "attempts": _sqlite_rows(destination.path, "attempts"),
        "attempt_events": _sqlite_rows(destination.path, "attempt_events"),
    }
    return cp_record, proposal.model_dump(mode="json", exclude_none=False), moltbot


def _effect_rows(destination):
    return _sqlite_rows(destination.path, "effects")


def test_actual_pinned_success_import_is_non_effecting(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    result = executor.execute(envelope=request, proposal=proposal, decision=decision, now=helper.NOW)
    assert result.status == "executed"
    assert destination.observe(decision.effect_id)["state"] == "applied"

    before = _effect_rows(destination)
    cp, p, m = _export_sources(workflow, proposal, request, result, destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    after = _effect_rows(destination)

    assert before == after
    assert len(after) == 1
    assert bundle.semantics.external_effect_execution is False
    assert bundle.semantics.independent_effect_verification is False
    assert any(r.record_type == "runtime_decision" for r in bundle.records)
    assert any(r.record_type == "destination_effect" for r in bundle.records)
    assert any(link.link_type == "explicit" for link in bundle.links)
    assert bundle.metadata["control_plane_revision"] == CP_REVISION
    assert bundle.metadata["moltbot_safe_revision"] == MOLTBOT_REVISION
    assert bundle.metadata["manifest_revision"] == MANIFEST_REVISION
    assert bundle.metadata["alvorada_revision"] == ALVORADA_REVISION



def test_actual_pinned_decision_hold_has_no_effect(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper = h._load_pinned_helpers()
    proposal = helper.proposal()
    resolver = helper.resolver_for(proposal)
    grant = resolver.contexts[helper.PROFILE]["grant"]
    resolver.statuses[grant["grant_id"]].status = "revoked"
    destination = helper.LocalRefundDestination(tmp_path / "cp-destination.json")
    records = helper.BoundedRecordStore(tmp_path / "cp-run.json", "run-1")
    workflow = helper.BoundedAuthorizationWorkflow(
        manifest=helper.manifest(),
        resolver=resolver,
        destination=destination,
        records=records,
    )

    decision = workflow.decide(proposal, now=helper.NOW)
    assert decision.result == "hold"
    assert "grant_not_active" in decision.reasons
    assert destination.snapshot()["effects"] == {}

    bundle = import_bounded_workflow(
        workflow.records.load().model_dump(mode="json"),
        proposal=proposal.model_dump(mode="json", exclude_none=False),
    )
    assert bundle.semantics.external_effect_execution is False
    assert destination.snapshot()["effects"] == {}
    assert any(
        record.record_type == "runtime_decision" and record.data["result"] == "hold"
        for record in bundle.records
    )


def test_actual_pinned_denied_revalidation_has_no_effect(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    grant = resolver.contexts[helper.PROFILE]["grant"]
    resolver.statuses[grant["grant_id"]].status = "revoked"

    result = executor.execute(envelope=request, proposal=proposal, decision=decision, now=helper.NOW)
    assert result.status == "denied"
    assert destination.observe(decision.effect_id)["state"] == "absent"

    cp, p, m = _export_sources(workflow, proposal, request, result, destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    assert _effect_rows(destination) == []
    assert bundle.semantics.external_effect_execution is False


def test_actual_pinned_lost_ack_preserves_unknown_then_applied_observation(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    result = executor.execute(
        envelope=request, proposal=proposal, decision=decision, now=helper.NOW, simulate="lost_ack"
    )
    assert result.status == "unknown"
    assert destination.observe(decision.effect_id)["state"] == "applied"

    before = _effect_rows(destination)
    cp, p, m = _export_sources(workflow, proposal, request, result, destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    assert _effect_rows(destination) == before

    cp_states = [
        r.data["status"] for r in bundle.records
        if r.record_type == "control_plane_attempt_transition"
    ]
    observations = [
        r.data["state"] for r in bundle.records
        if r.record_type == "effect_observation"
    ]
    assert cp_states[-1] == "unknown"
    assert observations[-1] == "applied"
    assert any(f.code == "M002" for f in bundle.import_reports[0].findings)


def test_actual_pinned_duplicate_restart_reconciles_without_second_effect(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    first = executor.execute(envelope=request, proposal=proposal, decision=decision, now=helper.NOW)
    assert first.status == "executed"
    assert len(_effect_rows(destination)) == 1

    restarted_destination = h.DurableRefundDestination(destination.root)
    restarted_executor = h.PinnedControlPlaneExecutor(
        workflow=workflow,
        destination=restarted_destination,
        policy=h.policy(request.operation),
    )
    second = restarted_executor.execute(
        envelope=request, proposal=proposal, decision=decision, now=helper.NOW
    )
    assert second.status == "reconciled"
    assert len(_effect_rows(restarted_destination)) == 1

    cp, p, m = _export_sources(workflow, proposal, request, second, restarted_destination)
    before = _effect_rows(restarted_destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    assert _effect_rows(restarted_destination) == before
    assert any(r.record_type == "reconciliation" for r in bundle.records)


def test_actual_pinned_partial_delivery_stays_partial(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    result = executor.execute(
        envelope=request, proposal=proposal, decision=decision, now=helper.NOW, simulate="partial"
    )
    assert result.status == "partial"
    assert destination.observe(decision.effect_id)["state"] == "partial"

    cp, p, m = _export_sources(workflow, proposal, request, result, destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    assert bundle.status == "reconstruction_partial"
    assert any(
        r.record_type == "effect_observation" and r.data["state"] == "partial"
        for r in bundle.records
    )


def test_actual_pinned_stale_evidence_prevents_execution(tmp_path):
    h = _load_actual_pinned_moltbot_helpers()
    helper, proposal, resolver, workflow, decision, destination, executor, request = h._integrated(tmp_path)
    resolver.evidence["urn:cognous:evidence:refund-entitlement"].observed_at = (
        helper.NOW - helper.timedelta(minutes=10)
    ).isoformat()

    result = executor.execute(envelope=request, proposal=proposal, decision=decision, now=helper.NOW)
    assert result.status == "denied"
    assert _effect_rows(destination) == []

    cp, p, m = _export_sources(workflow, proposal, request, result, destination)
    bundle = import_bounded_workflow(cp, proposal=p, moltbot_export=m)
    assert bundle.semantics.external_effect_execution is False
    assert _effect_rows(destination) == []
