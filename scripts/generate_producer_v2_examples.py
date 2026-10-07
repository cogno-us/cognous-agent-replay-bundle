#!/usr/bin/env python3
"""Execute pinned synthetic producers, then perform non-effecting Replay import.

No dependency edits. Fixture authority is synthetic and comes from the accepted
executor's test setup; execution/export/import use public component interfaces.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
from unittest.mock import patch

from agent_replay_bundle import import_bounded_workflow, ReconstructionBundle
from agent_replay_bundle.importers import CONTROL_PLANE_V2_REVISIONS, MOLTBOT_V2_REVISION, MANIFEST_REVISION
from agent_replay_bundle.reconstruction import content_digest


def main(output: Path):
    cp = Path(os.environ['ARB_V2_CONTROL_PLANE_ROOT']).resolve()
    executor_root = Path(os.environ['ARB_V2_MOLTBOT_ROOT']).resolve()
    manifest = Path(os.environ['ARB_PINNED_MANIFEST_FIXTURE']).resolve()
    cp_revision = subprocess.check_output(['git', '-C', str(cp), 'rev-parse', 'HEAD'], text=True).strip()
    if cp_revision not in CONTROL_PLANE_V2_REVISIONS:
        raise RuntimeError(f'wrong pinned Control Plane revision: {cp_revision}')
    for path, revision in ((executor_root, MOLTBOT_V2_REVISION), (manifest.parents[1], MANIFEST_REVISION)):
        actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision:
            raise RuntimeError(f'wrong pinned producer revision: {actual}')
    sys.path[:0] = [str(cp / 'src'), str(executor_root)]
    os.environ['MOLTBOT_SAFE_CONTROL_PLANE_ROOT'] = str(cp)
    os.environ['MOLTBOT_SAFE_MANIFEST_FIXTURE'] = str(manifest)
    spec = importlib.util.spec_from_file_location('v2_synthetic_fixture', executor_root / 'tests/test_safe_executor.py')
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    from engine.control_plane_adapter import ControlPlaneRefundDestinationAdapter, PinnedControlPlaneExecutor
    from engine.producer_contract import export_execution_artifacts
    from engine.safe_executor import DurableRefundDestination, snapshot_envelope

    output.mkdir(parents=True, exist_ok=True)
    cases, summaries = {}, {}
    for name in ('success', 'rejected_wrong_effect', 'rejected_stale', 'rejected_malformed',
                 'rejected_contradictory', 'unavailable', 'restart', 'rejected_restart', 'lost_ack', 'partial',
                 'prior_absence', 'denied', 'historical_applied', 'historical_absent'):
        with tempfile.TemporaryDirectory() as state:
            h,p,resolver,w,d,dest,e,request = helpers._integrated(Path(state))
            before_execution = dest.observe(d.effect_id)
            assert before_execution['state'] == 'absent'
            original = ControlPlaneRefundDestinationAdapter.observe
            def fault(adapter, effect_id):
                observation = original(adapter, effect_id)
                if adapter.outcome.result is not None:
                    if name in {'unavailable', 'restart'}:
                        raise OSError('synthetic unavailable post-dispatch observation')
                    if name in {'rejected_wrong_effect', 'rejected_restart'}:
                        observation.effect_id = 'rejected-unrelated-effect'
                    elif name == 'rejected_stale':
                        observation.observed_at = (h.NOW - h.timedelta(seconds=61)).isoformat()
                    elif name == 'rejected_malformed':
                        observation.observed_at = 'malformed'
                    elif name == 'rejected_contradictory':
                        observation.destination_state['state'] = 'absent'
                return observation
            if name == 'denied':
                w.observation_policy = None
            if name == 'prior_absence':
                with patch.object(dest, 'commit', side_effect=TimeoutError('synthetic before-commit interruption')):
                    first = e.execute(envelope=request, proposal=p, decision=d, now=h.NOW)
                assert first.status == 'unknown'
                rec = e.reconcile(request, now=h.NOW)
                assert rec.result == 'observed_absent' and not rec.retry_eligible
                result = e.execute(envelope=request, proposal=p, decision=d, now=h.NOW)
                assert result.status == 'denied'
            elif name == 'historical_absent':
                result = e.observe_historical(request)
            else:
                with patch.object(ControlPlaneRefundDestinationAdapter, 'observe', fault):
                    result = e.execute(envelope=request, proposal=p, decision=d, now=h.NOW,
                                       simulate=name if name in {'lost_ack', 'partial'} else None)
                if name in {'restart', 'rejected_restart'}:
                    assert result.observation is None and result.acknowledged
                    w.records = h.BoundedRecordStore(w.records.path, w.records.run_id)
                    dest = DurableRefundDestination(dest.root)
                    e = PinnedControlPlaneExecutor(workflow=w, destination=dest, policy=e.policy,
                                                    observation_clock=lambda: h.NOW)
                    result = e.execute(envelope=request, proposal=p, decision=d, now=h.NOW)
                    assert result.status == 'reconciled' and not result.newly_executed
                if name == 'historical_applied':
                    result = e.observe_historical(request)
            m = export_execution_artifacts(request, result, dest, repository_revision=MOLTBOT_V2_REVISION)
            expected_attempts = 0 if name in {'denied', 'historical_absent'} else 1
            assert len(m['attempts']) == expected_attempts
            source = {'control_plane_record': w.records.load().model_dump(mode='json'),
                      'proposal': p.model_dump(mode='json', exclude_none=False), 'moltbot_export': m,
                      'control_plane_revision': cp_revision}
            before_import = dest.observe(d.effect_id)
            count = dest.effect_count(request.operation.grant_id)
            expected_count = 0 if name in {'prior_absence', 'denied', 'historical_absent'} else 1
            assert count == expected_count
            if count:
                op = snapshot_envelope(request).operation
                assert before_import['destination_state'] == {
                    'effect_id': d.effect_id, 'state': 'partial' if name == 'partial' else 'applied',
                    'grant_id': op.grant_id, 'target': op.target, 'amount': op.amount,
                    'unit': op.unit, 'payload': op.payload(), 'operation_digest': op.digest}
            cp_before = w.records.path.read_bytes()
            def database_snapshot():
                with sqlite3.connect(dest.path) as db:
                    return list(db.iterdump())
            db_before = database_snapshot()
            bundle = import_bounded_workflow(**source)
            ReconstructionBundle.model_validate_json(bundle.model_dump_json())
            assert w.records.path.read_bytes() == cp_before
            assert database_snapshot() == db_before
            assert dest.observe(d.effect_id) == before_import
            assert dest.effect_count(request.operation.grant_id) == count
            assert not bundle.semantics.external_effect_execution
            assert not bundle.semantics.policy_reevaluation
            assert not bundle.semantics.independent_effect_verification
            cases[name] = source
            summaries[name] = {
                'decision_id': d.decision_id, 'effect_id': d.effect_id,
                'attempt_identity': m['attempt_identity'], 'effect_count_before_import': count,
                'effect_count_after_import': count, 'destination': before_import,
                'status': result.status, 'observed_state': result.observed_state,
                'reconstruction_status': bundle.status,
                'effect_observation_history': bundle.metadata['effect_observation_history'],
                'acknowledged': result.acknowledged, 'newly_executed': result.newly_executed,
                'records_unchanged': True,
                'executor_attempt_count': len(m['attempts']),
                'control_plane_attempt_ids': [a['attempt_id'] for a in m['control_plane_attempts']],
                'cp_record_sha256': hashlib.sha256(cp_before).hexdigest(),
                'logical_database_sha256': hashlib.sha256(json.dumps(db_before).encode()).hexdigest(),
                'bundle_digest': content_digest(bundle).value,
                'classification': 'required_safety_invariant_pass',
            }
            if name in {'success', 'rejected_wrong_effect', 'unavailable', 'prior_absence', 'restart'}:
                (output / f'producer_v2_{name}.json').write_text(bundle.model_dump_json(indent=2) + '\n')
    (output / 'producer_v2_sources.json').write_text(json.dumps(cases, indent=2) + '\n')
    (output / 'producer_v2_results.json').write_text(json.dumps({
        'pins': {'control_plane': cp_revision, 'executor': MOLTBOT_V2_REVISION, 'manifest': MANIFEST_REVISION},
        'scope': 'synthetic same-host SQLite; reconstruction is non-effecting; no independent verification',
        'scenarios': summaries}, indent=2) + '\n')
    print(f'{len(cases)} real-producer scenarios passed; destination and CP stores unchanged by import')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    main(parser.parse_args().output_dir)
