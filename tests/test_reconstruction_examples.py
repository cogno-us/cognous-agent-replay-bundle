from __future__ import annotations

import json
from pathlib import Path

from agent_replay_bundle.reconstruction import ReconstructionBundle


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_reconstruction_examples_validate_against_model():
    for name in (
        "bounded_success_reconstruction_v0_2.json",
        "bounded_lost_ack_reconstruction_v0_2.json",
    ):
        data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
        bundle = ReconstructionBundle.model_validate(data)
        assert bundle.bundle_version == "0.2.0"
        assert bundle.semantics.external_effect_execution is False
        assert bundle.semantics.independent_effect_verification is False


def test_lost_ack_example_keeps_unknown_and_later_applied_state():
    data = json.loads(
        (EXAMPLES / "bounded_lost_ack_reconstruction_v0_2.json").read_text(encoding="utf-8")
    )
    bundle = ReconstructionBundle.model_validate(data)
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
    assert transitions[-1] == "unknown"
    assert observations[-1] == "applied"
