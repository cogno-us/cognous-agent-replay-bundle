"""Tests for the loader module."""

import json
import tempfile
from pathlib import Path

import pytest

from agent_replay_bundle.loader import dump_replay_bundle, load_replay_bundle, load_replay_bundle_json
from agent_replay_bundle.models import AgentReplayBundle


MINIMAL_PAYLOAD = {
    "bundle_id": "bundle-001",
    "run_id": "run-001",
    "generated_at": "2026-01-01T00:00:00Z",
    "frame": {
        "frame_id": "frame-001",
        "task": "Test task",
        "actor": "test-agent",
        "environment": "test",
        "policy_version": "v1.0",
        "created_at": "2026-01-01T00:00:00Z",
    },
}


class TestLoadReplayBundle:
    def test_load_valid_bundle_from_file(self, tmp_path):
        f = tmp_path / "bundle.json"
        f.write_text(json.dumps(MINIMAL_PAYLOAD), encoding="utf-8")
        bundle = load_replay_bundle(f)
        assert isinstance(bundle, AgentReplayBundle)
        assert bundle.bundle_id == "bundle-001"

    def test_load_valid_bundle_from_string_path(self, tmp_path):
        f = tmp_path / "bundle.json"
        f.write_text(json.dumps(MINIMAL_PAYLOAD), encoding="utf-8")
        bundle = load_replay_bundle(str(f))
        assert bundle.bundle_id == "bundle-001"

    def test_file_not_found_raises_error(self):
        with pytest.raises(FileNotFoundError):
            load_replay_bundle("/nonexistent/path/bundle.json")

    def test_invalid_json_raises_value_error(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_replay_bundle(f)

    def test_model_validation_error_raises_value_error(self, tmp_path):
        f = tmp_path / "invalid.json"
        f.write_text(json.dumps({"bundle_id": "b1"}), encoding="utf-8")
        with pytest.raises(ValueError, match="model validation"):
            load_replay_bundle(f)


class TestLoadReplayBundleJson:
    def test_load_valid_payload(self):
        bundle = load_replay_bundle_json(MINIMAL_PAYLOAD)
        assert bundle.bundle_id == "bundle-001"

    def test_invalid_payload_raises(self):
        with pytest.raises(ValueError):
            load_replay_bundle_json({"bundle_id": "x"})


class TestDumpReplayBundle:
    def test_dump_writes_file(self, tmp_path):
        bundle = load_replay_bundle_json(MINIMAL_PAYLOAD)
        out = tmp_path / "output.json"
        result = dump_replay_bundle(bundle, out)
        assert result == out.resolve()
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["bundle_id"] == "bundle-001"

    def test_dump_creates_parent_dirs(self, tmp_path):
        bundle = load_replay_bundle_json(MINIMAL_PAYLOAD)
        out = tmp_path / "subdir" / "nested" / "output.json"
        dump_replay_bundle(bundle, out)
        assert out.exists()

    def test_dump_indented_json(self, tmp_path):
        bundle = load_replay_bundle_json(MINIMAL_PAYLOAD)
        out = tmp_path / "output.json"
        dump_replay_bundle(bundle, out)
        text = out.read_text()
        assert "\n" in text  # indented
