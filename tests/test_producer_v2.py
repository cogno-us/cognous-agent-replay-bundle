"""Real v2 producers run in a subprocess, isolated from historical runtime modules."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_replay_bundle import ReconstructionBundle, import_bounded_workflow
from agent_replay_bundle.importers import ImportContractError, CONTROL_PLANE_V2_REVISION


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    if not os.environ.get('ARB_V2_MOLTBOT_ROOT') or not os.environ.get('ARB_V2_CONTROL_PLANE_ROOT'):
        pytest.skip('accepted v2 producer checkouts not configured')
    output = tmp_path_factory.mktemp('producer-v2')
    subprocess.run([sys.executable, 'scripts/generate_producer_v2_examples.py', '--output-dir', str(output)], check=True)
    return json.loads((output / 'producer_v2_sources.json').read_text())


@pytest.mark.parametrize('name', ['success', 'rejected_wrong_effect', 'rejected_stale',
    'rejected_malformed', 'rejected_contradictory', 'unavailable', 'restart', 'lost_ack',
    'partial', 'prior_absence', 'denied', 'historical_applied', 'historical_absent'])
def test_real_producer_import(cases, name):
    source = cases[name]
    before = copy.deepcopy(source)
    bundle = import_bounded_workflow(**source)
    assert source == before
    restored = ReconstructionBundle.model_validate_json(bundle.model_dump_json())
    assert restored == bundle
    assert bundle.bundle_version == '0.2.0'
    assert bundle.metadata['control_plane_revision'] == CONTROL_PLANE_V2_REVISION
    assert not bundle.semantics.external_effect_execution
    assert not bundle.semantics.policy_reevaluation
    assert not bundle.semantics.independent_effect_verification
    result = source['moltbot_export']['execution_result']
    retained = next(r for r in bundle.records if r.record_type == 'execution_result')
    assert retained.data == result
    if name.startswith('rejected') or name == 'unavailable':
        assert result['acknowledged'] and result['newly_executed']
        assert result['observation'] is None and result['observed_state'] == 'unknown'
        assert bundle.status == 'reconstruction_partial'
        assert not any(r.record_type == 'executor_observation' for r in bundle.records)
        evidence = next(r for r in bundle.records if r.record_type == 'executor_control_plane_evidence')
        assert evidence.data == source['moltbot_export']['control_plane_evidence']
        assert any(r.record_type == 'moltbot_attributed_control_plane_attempt' for r in bundle.records)
    if name == 'rejected_wrong_effect':
        rejected = next(r for r in bundle.records if r.record_type == 'rejected_executor_observation')
        assert rejected.data['effect_id'] == 'rejected-unrelated-effect'
        assert rejected.identifiers == {} and rejected.evidence_class == 'producer_reported'
    if name == 'prior_absence':
        assert result['status'] == 'denied'
        assert not result['newly_executed']
        assert any(r.record_type == 'reconciliation' and r.data['result'] == 'observed_absent'
                   and r.data['retry_eligible'] is False for r in bundle.records)
    if name.startswith('historical'):
        assert result['control_plane_evidence'] == {}
        assert any(f.code == 'M020' for report in bundle.import_reports for f in report.findings)


@pytest.mark.parametrize('attack', [
    'unsupported_version', 'unsupported_revision', 'old_cp', 'unknown_cp',
    'enclosing_effect', 'enclosing_decision', 'dangling_attempt', 'conflicting_attempt',
    'missing_cp_attempt', 'copied_reconciliation', 'changed_reconciliation_both_copies',
    'promoted_rejection', 'contradictory_state', 'retry_permission', 'legacy_retry',
    'payload', 'target', 'amount', 'effect_state', 'missing_effect',
    'accepted_stale', 'accepted_wrong_effect', 'accepted_policy_missing',
    'acknowledgement_promotion', 'missing_rejected', 'missing_evidence',
    'cp_terminal_conflict', 'export_observation_promotion', 'dangling_prior_ack',
])
def test_adversarial_contract(cases, attack):
    source = copy.deepcopy(cases['rejected_wrong_effect' if attack in {
        'promoted_rejection', 'missing_rejected', 'export_observation_promotion',
        'contradictory_state', 'missing_effect'} else 'success'])
    m = source['moltbot_export']; result = m['execution_result']
    cp = source['control_plane_record']; rec = m['control_plane_evidence']['reconciliation']
    if attack == 'unsupported_version': m['producer_profile']['profile_version'] = '3.0.0'
    elif attack == 'unsupported_revision': m['repository']['revision'] = 'unknown'
    elif attack == 'old_cp': source.pop('control_plane_revision')
    elif attack == 'unknown_cp': source['control_plane_revision'] = 'unknown'
    elif attack == 'enclosing_effect': result['effect_id'] = 'other'
    elif attack == 'enclosing_decision': result['decision_id'] = 'other'
    elif attack == 'dangling_attempt': result['attempt_id'] = m['attempt_identity']['attempt_id'] = 'missing'
    elif attack == 'conflicting_attempt':
        row = copy.deepcopy(m['attempts'][0]); row['started_at'] = 'other'; m['attempts'].append(row)
    elif attack == 'missing_cp_attempt': cp['attempts'] = []
    elif attack == 'copied_reconciliation': cp['reconciliations'].pop()
    elif attack == 'changed_reconciliation_both_copies':
        rec['reconciled_at'] = 'changed'; result['control_plane_evidence']['reconciliation']['reconciled_at'] = 'changed'
    elif attack == 'promoted_rejection':
        result['observation'] = copy.deepcopy(rec['observation']); result['observed_state'] = 'applied'
        m['observations'] = [copy.deepcopy(result['observation'])]
    elif attack == 'export_observation_promotion': m['observations'] = [copy.deepcopy(rec['observation'])]
    elif attack == 'contradictory_state': result['observed_state'] = 'applied'
    elif attack == 'retry_permission': cp['reconciliations'][-1]['retry_eligible'] = True
    elif attack == 'legacy_retry': cp['reconciliations'][0]['result'] = 'safe_to_retry'
    elif attack == 'payload': m['effects'][0]['payload_json'] = '{"substituted":true}'
    elif attack == 'target': m['effects'][0]['target'] = 'substituted'
    elif attack == 'amount': m['effects'][0]['amount'] = 500
    elif attack == 'effect_state': m['effects'][0]['state'] = 'absent'
    elif attack == 'missing_effect': m['effects'] = []
    elif attack == 'accepted_stale': cp['reconciliations'][-1]['observation']['observed_at'] = '2000-01-01T00:00:00Z'
    elif attack == 'accepted_wrong_effect': cp['reconciliations'][-1]['observation']['effect_id'] = 'other'
    elif attack == 'accepted_policy_missing': cp['reconciliations'][-1]['observation_max_age_seconds'] = None
    elif attack == 'acknowledgement_promotion': result['acknowledged'] = False
    elif attack == 'missing_rejected': m['rejected_observations'] = []
    elif attack == 'missing_evidence': m.pop('control_plane_evidence')
    elif attack == 'dangling_prior_ack':
        row = copy.deepcopy(cp['attempts'][-1]); row['attempt_id'] = 'different-cp-attempt'
        row['acknowledgement']['attempt_id'] = 'unretained-executor-attempt'; cp['attempts'].append(row)
    elif attack == 'cp_terminal_conflict':
        row = copy.deepcopy(cp['attempts'][-1]); row['status'] = 'failed'; cp['attempts'].append(row)
    with pytest.raises(ImportContractError):
        import_bounded_workflow(**source)


def test_published_v2_examples_preserve_profiles_and_content():
    from agent_replay_bundle.reconstruction import content_digest
    results = json.loads(Path('docs/workstreams/producer_v2_results.json').read_text())['scenarios']
    for path in Path('examples/producer-v2').glob('*.json'):
        bundle = ReconstructionBundle.model_validate_json(path.read_text())
        profiles = {p.profile_id for p in bundle.producer_profiles}
        assert all(r.producer_profile_id in profiles for r in bundle.records)
        name = path.stem.removeprefix('producer_v2_')
        assert content_digest(bundle).value == results[name]['bundle_digest']
        assert all(r.evidence_class == 'producer_reported' for r in bundle.records)
        assert results[name]['effect_count_before_import'] == results[name]['effect_count_after_import']
        assert results[name]['records_unchanged']
