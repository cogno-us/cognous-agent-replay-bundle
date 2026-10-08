import json
from pathlib import Path

from agent_replay_bundle.importers import (
    CONTROL_PLANE_MERGED_REVISION,
    CONTROL_PLANE_REVISION,
    CONTROL_PLANE_V2_PERSISTENCE_REVISION,
    CONTROL_PLANE_V2_REVISION,
    LEGACY_MOLTBOT_SAFE_REVISION,
    MOLTBOT_MERGED_REVISION,
    MOLTBOT_SAFE_REVISION,
    MOLTBOT_V2_REVISION,
)
from agent_replay_bundle.reconstruction import RECONSTRUCTION_BUNDLE_VERSION


MATRIX = Path(__file__).parents[1] / "qualification" / "w3" / "producer-consumer-compatibility.json"


def _load():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_w3_matrix_matches_exact_current_replay_pairs():
    matrix = _load()
    pairs = matrix["supported_pairs"]
    observed = {
        (p.get("control_plane_revision"), p.get("executor_revision"))
        for p in pairs
        if p.get("control_plane_revision") and p.get("executor_revision")
    }
    assert observed == {
        (CONTROL_PLANE_REVISION, LEGACY_MOLTBOT_SAFE_REVISION),
        (CONTROL_PLANE_REVISION, MOLTBOT_SAFE_REVISION),
        (CONTROL_PLANE_V2_REVISION, MOLTBOT_V2_REVISION),
        (CONTROL_PLANE_V2_PERSISTENCE_REVISION, MOLTBOT_V2_REVISION),
        (CONTROL_PLANE_MERGED_REVISION, MOLTBOT_MERGED_REVISION),
    }
    assert {p["replay_bundle_version"] for p in pairs} == {RECONSTRUCTION_BUNDLE_VERSION}


def test_w3_future_semantics_are_prepared_not_claimed_supported():
    matrix = _load()
    prepared = {item["semantic"] for item in matrix["prepared_not_supported"]}
    assert {"tenant", "refusal", "stop", "effect_observation", "recovery", "optional_adapter_provenance"} <= prepared
    assert matrix["authority_boundary"].endswith("never grant, refresh, or authorize execution.")


def test_w3_evidence_states_are_distinct():
    states = _load()["evidence_states"]
    assert set(states) == {"missing", "incomplete", "unsupported", "unknown"}
    assert len(set(states.values())) == 4
