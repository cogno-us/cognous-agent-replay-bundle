import copy
import pytest
from tests.test_w3_c8_lineage import data
from agent_replay_bundle.w3_c8_lineage import import_c8_source,C8LineageError

@pytest.mark.parametrize("table,key,value",[
 ("authority_grants_v1","tenant_id","wrong-tenant"),
 ("authority_approvals_v1","grant_id","wrong-grant"),
 ("authority_policies_v1","tenant_id","wrong-tenant"),
 ("authority_grants_v1","revision","stale"),
 ("authority_approvals_v1","proposal_commitment",""),
 ("authority_policies_v1","version","stale"),
])
def test_invalid_authority_row_rejected(table,key,value):
    doc=data()
    doc["rows"][table][0][key]=value
    with pytest.raises(C8LineageError):
        import_c8_source(authority=doc)

def _stop():
    return {"generation":"c8-local-stop/0.1","lifecycle_id":"local-1","events":[
        {"event_id":f"evt-{i}","sequence":i,"lifecycle_id":"local-1","effect_id":"effect-1",
         "kind":kind,"observation":{"source":"local-controller"}}
        for i,kind in enumerate(("stop_requested","stop_acknowledged","dispatch_closed",
             "quiescence_observed","destination_reconciled"),start=1)]}

@pytest.mark.parametrize("mutator",[
    lambda s:s["events"][1].update(event_id="evt-1"),
    lambda s:s["events"][2].update(lifecycle_id="different"),
    lambda s:s["events"][3].update(effect_id="cross-effect"),
    lambda s:s["events"][4].update(sequence=1),
    lambda s:s["events"][2].update(kind="stop_acknowledged"),
])
def test_negative_stop_lifecycle_rejected(mutator):
    stop=_stop()
    mutator(stop)
    with pytest.raises(C8LineageError):
        import_c8_source(authority=data(),stop=stop)

def test_omitted_stop_is_partial_not_success():
    stop=_stop()
    stop["events"].pop(3)
    result=import_c8_source(authority=data(),stop=stop)
    assert result.status=="reconstruction_partial"
    assert any(f.code=="C8-STOP" for f in result.import_reports[0].findings)
