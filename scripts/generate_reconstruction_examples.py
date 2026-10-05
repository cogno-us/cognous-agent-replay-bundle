#!/usr/bin/env python3
"""Generate Reconstruction Bundle 0.2 examples from pinned producer runs.

This script must run with the pinned Control Plane and Moltbot Safe checkouts
configured through the same environment variables used by CI.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from agent_replay_bundle.importers import import_bounded_workflow


def _load_pinned_helpers():
    cp_root = Path(os.environ["ARB_PINNED_CONTROL_PLANE_ROOT"])
    molt_root = Path(os.environ["ARB_PINNED_MOLTBOT_ROOT"])
    manifest_path = os.environ["ARB_PINNED_MANIFEST_FIXTURE"]

    sys.path.insert(0, str(cp_root / "src"))
    sys.path.insert(0, str(molt_root))
    os.environ["MOLTBOT_SAFE_CONTROL_PLANE_ROOT"] = str(cp_root)
    os.environ["MOLTBOT_SAFE_MANIFEST_FIXTURE"] = manifest_path

    helper_path = molt_root / "tests" / "test_safe_executor.py"
    spec = importlib.util.spec_from_file_location("arb_example_pinned_helpers", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load pinned Moltbot helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sqlite_rows(path: Path, table: str) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid")]


def _export_sources(workflow, proposal, request, result, destination):
    return (
        workflow.records.load().model_dump(mode="json"),
        proposal.model_dump(mode="json", exclude_none=False),
        {
            "execution_envelope": {
                "version": request.version,
                "decision_id": request.decision_id,
                "effect_id": request.effect_id,
                "operation": {
                    **dataclasses.asdict(request.operation),
                    "requested_permissions": list(request.operation.requested_permissions),
                },
                "attempt_id": request.attempt_id,
            },
            "execution_result": dataclasses.asdict(result),
            "effects": _sqlite_rows(destination.path, "effects"),
            "attempts": _sqlite_rows(destination.path, "attempts"),
            "attempt_events": _sqlite_rows(destination.path, "attempt_events"),
        },
    )


def _generate(helper_module, *, lost_ack: bool):
    with tempfile.TemporaryDirectory(prefix="arb-example-") as temp:
        root = Path(temp)
        (
            pinned,
            proposal,
            _resolver,
            workflow,
            decision,
            destination,
            executor,
            request,
        ) = helper_module._integrated(root)

        result = executor.execute(
            envelope=request,
            proposal=proposal,
            decision=decision,
            now=pinned.NOW,
            simulate="lost_ack" if lost_ack else None,
        )
        expected = "unknown" if lost_ack else "executed"
        if result.status != expected:
            raise RuntimeError(f"unexpected pinned execution result: {result.status}")
        observed = destination.observe(decision.effect_id)
        if observed["state"] != "applied":
            raise RuntimeError(f"unexpected destination state: {observed['state']}")

        cp_record, proposal_record, moltbot_export = _export_sources(
            workflow, proposal, request, result, destination
        )
        bundle = import_bounded_workflow(
            cp_record, proposal=proposal_record, moltbot_export=moltbot_export
        )
        bundle.metadata["fixture_provenance"] = "generated_from_actual_pinned_producer_run"
        bundle.metadata["scenario"] = "lost_ack" if lost_ack else "success"
        return bundle.model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    helper_module = _load_pinned_helpers()

    cases = (
        ("bounded_success_reconstruction_v0_2.json", False),
        ("bounded_lost_ack_reconstruction_v0_2.json", True),
    )
    for name, lost_ack in cases:
        data = _generate(helper_module, lost_ack=lost_ack)
        (output / name).write_text(
            json.dumps(data, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        print(output / name)


if __name__ == "__main__":
    main()
