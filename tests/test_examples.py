"""Tests for example bundle files."""

import json
from pathlib import Path

import pytest

from agent_replay_bundle.loader import load_replay_bundle
from agent_replay_bundle.models import SignedReplayBundle
from agent_replay_bundle.validator import validate_replay_bundle

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

UNSIGNED_EXAMPLES = [
    "customer_service_replay_bundle.json",
    "internal_research_replay_bundle.json",
    "procurement_replay_bundle.json",
    "redacted_replay_bundle.json",
]


class TestExamplesLoad:
    @pytest.mark.parametrize("filename", UNSIGNED_EXAMPLES)
    def test_example_loads(self, filename):
        bundle = load_replay_bundle(EXAMPLES_DIR / filename)
        assert bundle.bundle_id is not None

    def test_signed_example_loads_as_signed_bundle(self):
        path = EXAMPLES_DIR / "signed_replay_bundle.json"
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        signed = SignedReplayBundle.model_validate(data)
        assert signed.signed_bundle_id is not None
        assert signed.replay_bundle.bundle_id is not None


class TestExamplesValidate:
    @pytest.mark.parametrize("filename", UNSIGNED_EXAMPLES)
    def test_example_validates_with_no_errors(self, filename):
        bundle = load_replay_bundle(EXAMPLES_DIR / filename)
        report = validate_replay_bundle(bundle)
        errors = [i for i in report.issues if i.severity.value == "error"]
        assert errors == [], f"{filename} has validation errors: {errors}"

    def test_redacted_example_validates_with_no_errors(self):
        bundle = load_replay_bundle(EXAMPLES_DIR / "redacted_replay_bundle.json")
        report = validate_replay_bundle(bundle)
        errors = [i for i in report.issues if i.severity.value == "error"]
        assert errors == []
