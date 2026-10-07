"""Explicit qualification; no optional skips can satisfy this profile."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from agent_replay_bundle import import_bounded_workflow, ReconstructionBundle
from agent_replay_bundle.importers import (
    CONTROL_PLANE_MERGED_REVISION, MOLTBOT_MERGED_REVISION,
    CONTROL_PLANE_V2_PERSISTENCE_REVISION, MOLTBOT_V2_REVISION, ImportContractError,
)

@pytest.fixture(scope='module')
def records(tmp_path_factory):
    for key in ('ARB_V2_CONTROL_PLANE_ROOT','ARB_V2_MOLTBOT_ROOT','ARB_PINNED_MANIFEST_FIXTURE'):
        assert os.environ.get(key), f'Required checkout missing: {key}'
    out=Path(os.environ.get('ARB_MERGED_RESULTS',tmp_path_factory.mktemp('merged-producer')))
    subprocess.run([sys.executable,'scripts/generate_producer_v2_examples.py','--output-dir',str(out)],check=True,timeout=120)
    results=json.loads((out/'producer_v2_results.json').read_text())
    assert results['pins']['control_plane']==CONTROL_PLANE_MERGED_REVISION
    assert results['pins']['executor']==MOLTBOT_MERGED_REVISION
    return json.loads((out/'producer_v2_sources.json').read_text()), results

@pytest.mark.parametrize('case',['success','rejected_wrong_effect','rejected_stale','rejected_malformed','rejected_contradictory','unavailable','restart','rejected_restart','lost_ack','partial','prior_absence','denied','historical_applied','historical_absent'])
def test_actual_merged_producer_roundtrip_is_non_effecting(records,case):
    sources,results=records;source=sources[case];before=copy.deepcopy(source)
    bundle=import_bounded_workflow(**source)
    assert source==before
    assert ReconstructionBundle.model_validate_json(bundle.model_dump_json())==bundle
    assert bundle.metadata['control_plane_revision']==CONTROL_PLANE_MERGED_REVISION
    contract=bundle.metadata['moltbot_producer_contract']
    assert contract['repository_revision']==MOLTBOT_MERGED_REVISION
    assert contract['compatible_control_plane_revisions']==[CONTROL_PLANE_MERGED_REVISION]
    assert not bundle.semantics.external_effect_execution
    assert not bundle.semantics.policy_reevaluation
    assert not bundle.semantics.independent_effect_verification
    assert results['scenarios'][case]['records_unchanged']
    assert results['scenarios'][case]['effect_count_before_import']==results['scenarios'][case]['effect_count_after_import']

@pytest.mark.parametrize('mutation',['old_cp_new_executor','new_cp_old_executor','unknown_cp','unknown_executor','wrong_effect'])
def test_unqualified_pairs_and_contradictions_remain_rejected(records,mutation):
    source=copy.deepcopy(records[0]['success'])
    if mutation=='old_cp_new_executor':source['control_plane_revision']=CONTROL_PLANE_V2_PERSISTENCE_REVISION
    elif mutation=='unknown_cp':source['control_plane_revision']='0'*40
    elif mutation in ('new_cp_old_executor','unknown_executor'):
        revision=MOLTBOT_V2_REVISION if mutation=='new_cp_old_executor' else '0'*40
        source['moltbot_export']['repository']['revision']=revision
        source['moltbot_export']['provenance']['source_asserted']['repository_revision']=revision
    else:source['moltbot_export']['effects'][0]['effect_id']='unrelated'
    with pytest.raises(ImportContractError):import_bounded_workflow(**source)
