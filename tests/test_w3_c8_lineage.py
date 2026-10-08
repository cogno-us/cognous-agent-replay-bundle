import pytest
import json
from agent_replay_bundle.w3_c8_lineage import import_c8_source,C8LineageError
def data():
    return {"generation":"c8-source-rows/0.1","claim_id":"c","rows":{
    "execution_claims_v1":[{"claim_id":"c","tenant_id":"t","grant_id":"g","grant_revision":"1","claim_json":json.dumps({"claim_id":"c","tenant_id":"t","grant_id":"g","grant_revision":"1","proposal_commitment":"digest","approval_state":[{"approval_ref":"a"}],"policy_state":[{"ref":"p","version":"1"}]})}],
    "authority_grants_v1":[{"grant_id":"g","tenant_id":"t","revision":"1"}],
    "authority_approvals_v1":[{"approval_ref":"a","grant_id":"g","tenant_id":"t","proposal_commitment":"digest"}],
    "authority_policies_v1":[{"ref":"p","tenant_id":"t","version":"1"}]}}
def test_tenant_mismatch_rejected():
    x=data();x["rows"]["authority_approvals_v1"][0]["tenant_id"]="other"
    with pytest.raises(C8LineageError):import_c8_source(authority=x)
def test_absent_stop_explicit_partial():
    b=import_c8_source(authority=data());assert b.status=="reconstruction_partial"
    assert any(f.code=="C8-STOP" for f in b.import_reports[0].findings)
def test_stop_order_fails():
    stop={"generation":"c8-local-stop/0.1","lifecycle_id":"s","events":[
      {"event_id":"2","sequence":2,"lifecycle_id":"s","effect_id":"e","kind":"stop_acknowledged"},
      {"event_id":"1","sequence":1,"lifecycle_id":"s","effect_id":"e","kind":"stop_requested"}]}
    with pytest.raises(C8LineageError):import_c8_source(authority=data(),stop=stop)
