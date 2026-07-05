"""Tests for the CLI module."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
VALID_BUNDLE = EXAMPLES_DIR / "customer_service_replay_bundle.json"


def run_arb(*args):
    """Run the arb CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_replay_bundle.cli"] + list(args),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestValidateCommand:
    def test_validate_valid_example_returns_0(self):
        rc, out, err = run_arb("validate", str(VALID_BUNDLE))
        assert rc == 0
        assert "VALID" in out

    def test_validate_invalid_bundle_returns_1(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({
            "bundle_id": "",
            "run_id": "run-001",
            "generated_at": "2026-01-01T00:00:00Z",
            "frame": {
                "frame_id": "f1",
                "task": "t",
                "actor": "a",
                "environment": "e",
                "policy_version": "v1",
                "created_at": "2026-01-01T00:00:00Z",
            },
        }))
        rc, out, err = run_arb("validate", str(bad))
        assert rc == 1
        assert "INVALID" in out

    def test_file_not_found_returns_2(self):
        rc, out, err = run_arb("validate", "/nonexistent/path.json")
        assert rc == 2


class TestSummarizeCommand:
    def test_summarize_returns_0(self):
        rc, out, err = run_arb("summarize", str(VALID_BUNDLE))
        assert rc == 0
        assert "bundle_id" in out
        assert "run_id" in out
        assert "actor" in out

    def test_summarize_file_not_found_returns_2(self):
        rc, out, err = run_arb("summarize", "/nonexistent/file.json")
        assert rc == 2


class TestRedactCommand:
    def test_redact_writes_output(self, tmp_path):
        out_path = tmp_path / "redacted.json"
        rc, out, err = run_arb(
            "redact", str(VALID_BUNDLE),
            "--out", str(out_path),
        )
        assert rc == 0
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert data["status"] == "redacted"

    def test_redact_with_targets_and_final_output(self, tmp_path):
        out_path = tmp_path / "redacted.json"
        rc, out, err = run_arb(
            "redact", str(VALID_BUNDLE),
            "--out", str(out_path),
            "--targets",
            "--final-output",
        )
        assert rc == 0
        data = json.loads(out_path.read_text())
        assert data["final_output"] == "[REDACTED]"


class TestSignCommand:
    def test_sign_writes_output(self, tmp_path):
        out_path = tmp_path / "signed.json"
        rc, out, err = run_arb(
            "sign", str(VALID_BUNDLE),
            "--secret", "test-secret",
            "--out", str(out_path),
        )
        assert rc == 0
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "signed_bundle_id" in data
        assert data["signature_metadata"]["signed"] is True


class TestVerifyCommand:
    def test_verify_returns_0_for_signed_bundle(self, tmp_path):
        # First sign a bundle
        signed_path = tmp_path / "signed.json"
        run_arb(
            "sign", str(VALID_BUNDLE),
            "--secret", "my-secret",
            "--out", str(signed_path),
        )
        # Then verify it
        rc, out, err = run_arb("verify", str(signed_path), "--secret", "my-secret")
        assert rc == 0
        assert "VALID" in out

    def test_verify_returns_1_for_wrong_secret(self, tmp_path):
        signed_path = tmp_path / "signed.json"
        run_arb(
            "sign", str(VALID_BUNDLE),
            "--secret", "correct-secret",
            "--out", str(signed_path),
        )
        rc, out, err = run_arb("verify", str(signed_path), "--secret", "wrong-secret")
        assert rc == 1
        assert "INVALID" in out

    def test_verify_file_not_found_returns_2(self):
        rc, out, err = run_arb("verify", "/nonexistent/path.json", "--secret", "s")
        assert rc == 2
