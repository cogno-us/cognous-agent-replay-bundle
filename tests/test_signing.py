"""Tests for the signing module."""

import pytest

from agent_replay_bundle.models import (
    ActionProposal,
    ActionType,
    AgentReplayBundle,
    RunFrame,
    SignatureMetadata,
    SignedReplayBundle,
)
from agent_replay_bundle.signing import (
    canonical_bundle_json,
    sign_replay_bundle,
    verify_signed_replay_bundle,
)


def make_bundle(**kwargs):
    defaults = {
        "bundle_id": "bundle-001",
        "run_id": "run-001",
        "generated_at": "2026-01-01T00:00:00Z",
        "frame": RunFrame(
            frame_id="frame-001",
            task="Task",
            actor="agent",
            environment="test",
            policy_version="v1",
            created_at="2026-01-01T00:00:00Z",
        ),
    }
    defaults.update(kwargs)
    return AgentReplayBundle(**defaults)


class TestSigning:
    def test_signing_creates_signed_bundle(self):
        bundle = make_bundle()
        signed = sign_replay_bundle(bundle, "secret")
        assert isinstance(signed, SignedReplayBundle)
        assert signed.signature_metadata.signed is True
        assert signed.signature_metadata.signature_algorithm == "HMAC-SHA256"
        assert signed.signature_metadata.signature is not None

    def test_signing_records_key_id(self):
        bundle = make_bundle()
        signed = sign_replay_bundle(bundle, "secret", key_id="key-001")
        assert signed.signature_metadata.key_id == "key-001"

    def test_verification_succeeds_with_correct_secret(self):
        bundle = make_bundle()
        signed = sign_replay_bundle(bundle, "correct-secret")
        assert verify_signed_replay_bundle(signed, "correct-secret") is True

    def test_verification_fails_with_wrong_secret(self):
        bundle = make_bundle()
        signed = sign_replay_bundle(bundle, "correct-secret")
        assert verify_signed_replay_bundle(signed, "wrong-secret") is False

    def test_signature_changes_if_content_changes(self):
        bundle1 = make_bundle()
        bundle2 = make_bundle(bundle_id="bundle-002")
        signed1 = sign_replay_bundle(bundle1, "secret")
        signed2 = sign_replay_bundle(bundle2, "secret")
        assert signed1.signature_metadata.signature != signed2.signature_metadata.signature

    def test_verify_returns_false_for_empty_signature(self):
        from agent_replay_bundle.models import SignatureMetadata
        bundle = make_bundle()
        sig = SignatureMetadata(signed=True, signature_algorithm="HMAC-SHA256", signature=None)
        signed = SignedReplayBundle(
            signed_bundle_id="test",
            replay_bundle=bundle,
            signature_metadata=sig,
        )
        assert verify_signed_replay_bundle(signed, "secret") is False


class TestCanonicalSerialization:
    def test_canonical_json_is_string(self):
        bundle = make_bundle()
        result = canonical_bundle_json(bundle)
        assert isinstance(result, str)

    def test_canonical_json_is_stable(self):
        bundle = make_bundle()
        result1 = canonical_bundle_json(bundle)
        result2 = canonical_bundle_json(bundle)
        assert result1 == result2

    def test_canonical_json_excludes_signature(self):
        bundle = make_bundle(
            signature_metadata=SignatureMetadata(
                signed=True,
                signature="supersecret",
                signature_algorithm="HMAC-SHA256",
            )
        )
        canonical = canonical_bundle_json(bundle)
        assert "supersecret" not in canonical
        assert "signature_metadata" not in canonical

    def test_canonical_json_ignores_embedded_signature_metadata(self):
        bundle_without_signature_metadata = make_bundle()
        bundle_with_signature_metadata = make_bundle(
            signature_metadata=SignatureMetadata(
                signed=True,
                signed_at="2026-01-01T00:00:01Z",
                signature="embedded-signature",
                signature_algorithm="HMAC-SHA256",
                key_id="key-001",
            )
        )

        assert canonical_bundle_json(bundle_without_signature_metadata) == canonical_bundle_json(bundle_with_signature_metadata)

    def test_verification_succeeds_with_embedded_signature_metadata_and_correct_secret(self):
        bundle = make_bundle(
            signature_metadata=SignatureMetadata(
                signed=True,
                signed_at="2026-01-01T00:00:01Z",
                signature="stale-signature",
                signature_algorithm="HMAC-SHA256",
                key_id="embedded-key",
            )
        )

        signed = sign_replay_bundle(bundle, "correct-secret")
        assert verify_signed_replay_bundle(signed, "correct-secret") is True

    def test_verification_fails_with_embedded_signature_metadata_and_wrong_secret(self):
        bundle = make_bundle(
            signature_metadata=SignatureMetadata(
                signed=True,
                signed_at="2026-01-01T00:00:01Z",
                signature="stale-signature",
                signature_algorithm="HMAC-SHA256",
                key_id="embedded-key",
            )
        )

        signed = sign_replay_bundle(bundle, "correct-secret")
        assert verify_signed_replay_bundle(signed, "wrong-secret") is False

    def test_canonical_json_sorted_keys(self):
        import json
        bundle = make_bundle()
        canonical = canonical_bundle_json(bundle)
        # Verify it can be parsed back
        data = json.loads(canonical)
        assert data["bundle_id"] == "bundle-001"
