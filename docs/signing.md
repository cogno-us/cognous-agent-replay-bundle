# Signing

This document describes the export integrity signing provided by Agent Replay Bundle.

## Purpose

Signing a replay bundle provides **export integrity**: a verifiable record that the bundle has not been modified since it was signed. This is useful for sharing bundles across systems, storing them in audit logs, or attaching them to incident reports.

## Algorithm

Agent Replay Bundle uses **HMAC-SHA256** with a caller-supplied secret.

## Limitation

**This is export integrity, not production key management.**

HMAC-SHA256 with a shared secret does not provide:
- Non-repudiation (the signer's identity is not proven)
- Protection against compromise of the signing secret
- A PKI-based trust hierarchy

For high-assurance production use cases, use a proper key management system and consider asymmetric signing (e.g., Ed25519 or RSA-PSS with an HSM or KMS).

## Usage

### Signing

```python
from agent_replay_bundle.loader import load_replay_bundle
from agent_replay_bundle.signing import sign_replay_bundle

bundle = load_replay_bundle("my_bundle.json")
signed = sign_replay_bundle(bundle, secret="my-secret", key_id="key-001")

import json
with open("signed.json", "w") as f:
    json.dump(signed.model_dump(mode="json"), f, indent=2)
```

### Verification

```python
import json
from agent_replay_bundle.models import SignedReplayBundle
from agent_replay_bundle.signing import verify_signed_replay_bundle

with open("signed.json") as f:
    data = json.load(f)

signed = SignedReplayBundle.model_validate(data)
is_valid = verify_signed_replay_bundle(signed, secret="my-secret")
print("Valid" if is_valid else "Invalid")
```

### CLI

```bash
arb sign examples/customer_service_replay_bundle.json \
    --secret "my-secret" \
    --out /tmp/signed.json \
    --key-id "key-001"

arb verify /tmp/signed.json --secret "my-secret"
```

## Canonical serialization

The canonical form of a bundle is produced by:

1. Calling `bundle.model_dump(mode="json")`
2. Removing the entire `signature_metadata` field from the `AgentReplayBundle` payload
3. Serializing with `sort_keys=True`, compact separators `(",", ":")`, and `ensure_ascii=True`

The canonical form is stable: the same bundle will always produce the same canonical string when all non-signature fields match, regardless of any embedded `signature_metadata`.

## SignatureMetadata

After signing, the bundle's `signature_metadata` is populated with:

```json
{
  "signed": true,
  "signed_at": "2026-07-01T12:00:00Z",
  "signature_algorithm": "HMAC-SHA256",
  "signature": "<hex digest>",
  "key_id": "key-001"
}
```

## SignedReplayBundle

The output of signing is a `SignedReplayBundle`:

```json
{
  "signed_bundle_id": "signed-bundle-cs-001-abcd1234",
  "replay_bundle": { ... },
  "signature_metadata": { ... }
}
```

`SignedReplayBundle.signature_metadata` is the authoritative signature metadata for signed exports.

`AgentReplayBundle.signature_metadata` is optional embedded metadata for systems that store signature state directly on the bundle. It is not part of the canonical signing payload.
