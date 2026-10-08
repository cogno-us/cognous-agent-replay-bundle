import pytest

from agent_replay_bundle.w3_atomic_import import (
    AtomicEvidenceContractError, W2_RUNTIME_REVISION,
    import_w2_atomic_failure_history,
)

def _failure(**change):
    d = dict(failure_id="failure-1", effect_id="effect-1",
        decision_id="decision-1",attempt_id=None,stage="pre_dispatch",
        failure_class="policy_denial",reason_code="local_policy_rejected")
    d.update(change)
    return d

def _import(rows=None, **kw):
    return import_w2_atomic_failure_history(
        runtime_revision=W2_RUNTIME_REVISION,effect_id="effect-1",
        decision_id="decision-1",
        failure_records=[_failure()] if rows is None else rows, **kw)

def test_predispatch_refusal_has_no_fabricated_attempt():
    bundle=_import(attempt_records=[],observation={"status":"hold","retry_eligible":False})
    assert bundle.status=="reconstruction_complete"
    assert not bundle.links
    assert len([r for r in bundle.records if r.record_type=="atomic_attempt"])==0
    assert bundle.semantics.external_effect_execution is False

def test_lost_ack_retains_real_attempt_and_unknown_ack():
    attempt={"attempt_id":"attempt-1","effect_id":"effect-1","decision_id":"decision-1"}
    failure=_failure(failure_class="dispatch_error",stage="post_dispatch",
        reason_code="acknowledgement_unavailable",attempt_id="attempt-1")
    bundle=_import([failure],attempt_records=[attempt],
        observation={"effect_id":"effect-1","status":"applied","retry_eligible":False})
    assert len(bundle.links)==1
    assert bundle.records[-1].data["status"]=="applied"
    assert bundle.records[1].data["reason_code"]=="acknowledgement_unavailable"
    assert bundle.semantics.independent_effect_verification is False

def test_missing_evidence_is_partial_not_completed():
    bundle=_import()
    assert bundle.status=="reconstruction_partial"
    assert {f.code for f in bundle.import_reports[0].findings}=={"W3A01","W3A03"}

@pytest.mark.parametrize("mut",[
    {"effect_id":"other"},{"decision_id":"other"},{"failure_id":""},
    {"stage":"post_dispatch"},{"stage":"pre_dispatch","attempt_id":"invented"},
    {"failure_class":"unknown_class"},
])
def test_inconsistent_failure_lineage_fails_closed(mut):
    with pytest.raises(AtomicEvidenceContractError):
        _import([_failure(**mut)])

def test_missing_owning_attempt_fails_closed():
    with pytest.raises(AtomicEvidenceContractError):
        _import([_failure(stage="post_dispatch",failure_class="dispatch_error",
            attempt_id="attempt-missing")],attempt_records=[])

def test_unknown_revision_rejected():
    with pytest.raises(AtomicEvidenceContractError):
        import_w2_atomic_failure_history(runtime_revision="unaccepted",
            effect_id="effect-1",decision_id="decision-1",failure_records=[])

def test_retry_authority_not_inferred():
    with pytest.raises(AtomicEvidenceContractError):
        _import(attempt_records=[],observation={"retry_eligible":True})
