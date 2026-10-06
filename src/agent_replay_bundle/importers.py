"""Revision-pinned producer import adapters."""

from __future__ import annotations

import hashlib
from typing import Any

from .reconstruction import (
    CANONICAL_JSON_PROFILE,
    CommitmentRecord,
    ImportFinding,
    ImportReport,
    ProducerProfile,
    ReconstructionBundle,
    RecordLink,
    SourceRecord,
    canonical_bytes,
)

CONTROL_PLANE_REVISION = "283500652d47a692fb0b99a1172a6d5faffbd9a7"
LEGACY_MOLTBOT_SAFE_REVISION = "6b0ba1185bcd390f71df947dda349415e4105f5f"
MOLTBOT_SAFE_REVISION = "a4df7a925ca1b820b9958c479ce28616547cc6d0"
MOLTBOT_EXECUTOR_PROFILE = "urn:cognous:profiles:moltbot-safe-executor-evidence:1.0.0"
MOLTBOT_EXECUTOR_PROFILE_VERSION = "1.0.0"
MANIFEST_REVISION = "46c950bed37fe3812000895430bc0312d29e37ce"
ALVORADA_REVISION = "fb3d97938969a89e149e8ff8db2756091d1233fc"

LEGACY_PROFILE = "control-plane-legacy-replay@28350065"
BOUNDED_PROFILE = "control-plane-bounded-run@28350065"
LEGACY_MOLTBOT_PROFILE = "moltbot-safe-envelope-0.2.0@6b0ba118"
MOLTBOT_PROFILE = "moltbot-safe-executor-evidence-1.0.0@a4df7a9"


def _resolve_moltbot_compatibility(source: dict[str, Any]) -> dict[str, Any]:
    declared = source.get("producer_profile")
    if declared is None:
        return {
            "profile_id": LEGACY_MOLTBOT_PROFILE,
            "revision": LEGACY_MOLTBOT_SAFE_REVISION,
            "format_version": "0.2.0",
            "producer_contract_version": None,
            "repository_revision_provenance": "revision_pinned_legacy",
            "independently_established_provenance": False,
            "legacy_unversioned": True,
        }
    declared = _obj(declared, "moltbot_export.producer_profile")
    expected = {
        "profile": MOLTBOT_EXECUTOR_PROFILE,
        "profile_version": MOLTBOT_EXECUTOR_PROFILE_VERSION,
        "schema_version": "1.0.0",
        "execution_envelope_version": "0.2.0",
        "repository_revision": MOLTBOT_SAFE_REVISION,
        "repository_revision_provenance": "source_asserted",
        "independently_established_provenance": False,
    }
    for field, value in expected.items():
        _require_equal(
            declared.get(field),
            value,
            "moltbot_export.producer_profile." + field,
        )
    bindings = _obj(source.get("bindings"), "moltbot_export.bindings")
    envelope = _obj(source.get("execution_envelope"), "moltbot_export.execution_envelope")
    result = _obj(source.get("execution_result"), "moltbot_export.execution_result")
    _require_equal(bindings.get("decision_id"), envelope.get("decision_id"), "moltbot_export.bindings.decision_id")
    _require_equal(bindings.get("effect_id"), envelope.get("effect_id"), "moltbot_export.bindings.effect_id")
    _require_equal(result.get("decision_id"), envelope.get("decision_id"), "moltbot_export.execution_result.decision_id")
    _require_equal(result.get("effect_id"), envelope.get("effect_id"), "moltbot_export.execution_result.effect_id")
    operation = _obj(envelope.get("operation"), "moltbot_export.execution_envelope.operation")
    _require_equal(
        bindings.get("operation_digest"),
        _sha256(operation),
        "moltbot_export.bindings.operation_digest",
    )
    return {
        "profile_id": MOLTBOT_PROFILE,
        "revision": MOLTBOT_SAFE_REVISION,
        "format_version": "1.0.0",
        "producer_contract_version": MOLTBOT_EXECUTOR_PROFILE_VERSION,
        "repository_revision_provenance": "source_asserted",
        "independently_established_provenance": False,
        "legacy_unversioned": False,
    }


class ImportContractError(ValueError):
    """Producer data violates the pinned import contract."""


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _obj(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ImportContractError(f"{path} must be an object")
    return value


def _record(profile: str, kind: str, seq: int, path: str, data: dict[str, Any],
            *, ids: dict[str, Any] | None = None, at: str | None = None) -> SourceRecord:
    return SourceRecord(
        record_id=f"{profile}:{kind}:{seq}",
        producer_profile_id=profile,
        record_type=kind,
        source_sequence=seq,
        source_path=path,
        recorded_at=at,
        identifiers={k: str(v) for k, v in (ids or {}).items() if v not in (None, "")},
        data=data,
    )


def _unique_or_same(seen: dict[str, dict[str, Any]], key: str, value: dict[str, Any],
                    label: str) -> None:
    old = seen.get(key)
    if old is None:
        seen[key] = value
    elif old != value:
        raise ImportContractError(f"conflicting content under immutable {label} {key}")


def _require_equal(actual: Any, expected: Any, path: str) -> None:
    if actual != expected:
        raise ImportContractError(f"{path} conflicts with committed operation")


def _proposal_commitment(proposal: dict[str, Any]) -> str:
    return _sha256(proposal)


def _validate_proposal_binding(proposal: dict[str, Any], binding: dict[str, Any], path: str) -> None:
    expected_commitment = _proposal_commitment(proposal)
    _require_equal(binding.get("proposal_commitment"), expected_commitment, path + ".proposal_commitment")
    fields = (
        "manifest_id", "manifest_version", "manifest_digest", "actor", "principal",
        "action_id", "adapter_id", "target", "payload_commitment",
        "requested_permissions", "amount", "unit", "effects", "requirement_id",
    )
    for field in fields:
        actual = binding.get(field)
        expected = proposal.get(field)
        if field == "requested_permissions" and isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            actual, expected = list(actual), list(expected)
        _require_equal(actual, expected, path + "." + field)


def _validate_envelope_chain(
    op: dict[str, Any], proposal: dict[str, Any], binding: dict[str, Any]
) -> None:
    proposal_fields = (
        "actor", "principal", "manifest_id", "manifest_version", "manifest_digest",
        "action_id", "adapter_id", "target", "payload", "payload_commitment",
        "requested_permissions", "amount", "unit", "effects", "requirement_id",
    )
    for field in proposal_fields:
        actual = op.get(field)
        expected = proposal.get(field)
        if field == "requested_permissions" and isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            actual, expected = list(actual), list(expected)
        _require_equal(actual, expected, "execution_envelope.operation." + field)
    _require_equal(
        op.get("authority_context_id"), proposal.get("authority_context_ref"),
        "execution_envelope.operation.authority_context_id(profile_ref)",
    )
    _require_equal(
        op.get("proposal_commitment"), _proposal_commitment(proposal),
        "execution_envelope.operation.proposal_commitment",
    )
    for field in ("grant_id", "grant_revision", "effective_max_effects"):
        _require_equal(op.get(field), binding.get(field), "execution_envelope.operation." + field)


def _decode_payload_json(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ImportContractError(f"{path} must be canonical JSON text")
    try:
        decoded = __import__("json").loads(value)
    except (TypeError, ValueError) as exc:
        raise ImportContractError(f"{path} is invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ImportContractError(f"{path} must decode to an object")
    return decoded


def _validate_observation_content(observation: dict[str, Any], effect_id: str, op: dict[str, Any], path: str) -> None:
    _require_equal(observation.get("effect_id"), effect_id, path + ".effect_id")
    state = observation.get("state")
    destination = observation.get("destination_state")
    if state in {"applied", "partial"}:
        if not isinstance(destination, dict):
            raise ImportContractError(f"{path}.destination_state must be an object")
        for field in ("effect_id", "grant_id", "target", "amount", "unit"):
            expected = effect_id if field == "effect_id" else op.get(field)
            _require_equal(destination.get(field), expected, path + ".destination_state." + field)
        _require_equal(destination.get("payload"), op.get("payload"), path + ".destination_state.payload")
        if "operation_digest" in destination:
            _require_equal(destination.get("operation_digest"), _sha256(op), path + ".destination_state.operation_digest")


def import_legacy_control_plane_replay(source: dict[str, Any]) -> ReconstructionBundle:
    """Import the legacy ReplayBundle at the pinned Control Plane revision.

    Confirmed mappings are replay_bundle_id -> source_bundle_id,
    actions -> action_proposal records, and decisions -> policy_decision records.
    The source format has no embedded format version, so compatibility is
    revision-pinned rather than inferred from shape.
    """
    source = _obj(source, "source")
    required = {
        "replay_bundle_id", "run_id", "generated_at", "frame", "actions", "decisions",
        "policy_traces", "authority_records", "reliance_records", "blocked_actions",
    }
    missing = sorted(required - set(source))
    if missing:
        raise ImportContractError("legacy ReplayBundle missing: " + ",".join(missing))

    profile = ProducerProfile(
        profile_id=LEGACY_PROFILE,
        producer="Cognous Agent Control Plane",
        repository="cogno-us/cognous-agent-control-plane",
        revision=CONTROL_PLANE_REVISION,
        format_name="ReplayBundle",
        format_version=None,
        notes="No embedded format version; adapter is pinned to producer revision.",
    )
    report = ImportReport(
        adapter_profile=LEGACY_PROFILE,
        source_revision=CONTROL_PLANE_REVISION,
        complete=True,
        field_mappings={
            "replay_bundle_id": "metadata.source_bundle_id",
            "actions": "records[action_proposal]",
            "decisions": "records[policy_decision]",
            "policy_traces": "records[policy_trace]",
            "authority_records": "records[authority_record]",
            "reliance_records": "records[reliance_record]",
            "blocked_actions": "records[blocked_action]",
        },
    )
    records: list[SourceRecord] = []
    seq = 0
    frame = _obj(source["frame"], "frame")
    records.append(_record(LEGACY_PROFILE, "run_frame", seq, "frame", frame,
                           ids={"run_id": source["run_id"], "frame_id": frame.get("frame_id")},
                           at=frame.get("created_at")))
    seq += 1

    specs = (
        ("actions", "action_proposal", "action_id", "proposed_at"),
        ("decisions", "policy_decision", "decision_id", "decided_at"),
        ("policy_traces", "policy_trace", "trace_id", "evaluated_at"),
        ("authority_records", "authority_record", "authority_id", "created_at"),
        ("reliance_records", "reliance_record", "reliance_id", "created_at"),
        ("blocked_actions", "blocked_action", "blocked_id", "blocked_at"),
    )
    for field, kind, id_field, time_field in specs:
        values = source[field]
        if not isinstance(values, list):
            raise ImportContractError(f"{field} must be an array")
        for i, raw in enumerate(values):
            raw = _obj(raw, f"{field}[{i}]")
            records.append(_record(
                LEGACY_PROFILE, kind, seq, f"{field}[{i}]", raw,
                ids={"run_id": raw.get("run_id", source["run_id"]),
                     id_field: raw.get(id_field), "action_id": raw.get("action_id")},
                at=raw.get(time_field),
            ))
            seq += 1

    if "final_output" in source:
        records.append(_record(
            LEGACY_PROFILE, "final_output", seq, "final_output",
            {"value": source.get("final_output")}, ids={"run_id": source["run_id"]},
        ))

    extras = sorted(set(source) - required - {"final_output"})
    for field in extras:
        report.complete = False
        report.findings.append(ImportFinding(
            code="L001", category="unmapped_field", severity="warning", path=field,
            message="Field is outside the pinned legacy producer contract.",
        ))

    return ReconstructionBundle(
        run_id=str(source["run_id"]),
        status="reconstruction_complete" if report.complete else "reconstruction_partial",
        producer_profiles=[profile],
        records=records,
        import_reports=[report],
        metadata={
            "source_bundle_id": source["replay_bundle_id"],
            "source_generated_at": source["generated_at"],
            "source_format_version": None,
        },
    )


def import_bounded_workflow(
    control_plane_record: dict[str, Any],
    *,
    proposal: dict[str, Any] | None = None,
    moltbot_export: dict[str, Any] | None = None,
) -> ReconstructionBundle:
    """Import bounded Control Plane events and optional Moltbot destination evidence."""
    cp = _obj(control_plane_record, "control_plane_record")
    required = {"run_id", "decisions", "attempts", "observations", "reconciliations"}
    missing = sorted(required - set(cp))
    if missing:
        raise ImportContractError("BoundedRunRecord missing: " + ",".join(missing))
    run_id = cp["run_id"]
    if not isinstance(run_id, str) or not run_id:
        raise ImportContractError("run_id must be a non-empty string")

    report = ImportReport(
        adapter_profile=BOUNDED_PROFILE,
        source_revision=CONTROL_PLANE_REVISION,
        complete=True,
        field_mappings={
            "decisions": "records[runtime_decision]",
            "attempts": "records[control_plane_attempt_transition]",
            "observations": "records[effect_observation]",
            "reconciliations": "records[reconciliation]",
        },
    )
    for field in sorted(set(cp) - required):
        report.complete = False
        report.findings.append(ImportFinding(
            code="B001", category="unmapped_field", severity="warning", path=field,
            message="Unknown top-level bounded record field.",
        ))

    records: list[SourceRecord] = []
    links: list[RecordLink] = []
    commitments: list[CommitmentRecord] = []
    seq = 0

    if proposal is not None:
        p = _obj(proposal, "proposal")
        if p.get("run_id") not in (None, run_id):
            raise ImportContractError("proposal.run_id conflicts with bounded run_id")
        prec = _record(
            BOUNDED_PROFILE, "runtime_proposal", seq, "proposal", p,
            ids={
                "run_id": p.get("run_id") or run_id,
                "correlation_id": p.get("correlation_id"),
                "action_id": p.get("action_id"),
                "manifest_id": p.get("manifest_id"),
                "authority_context_profile_ref": p.get("authority_context_ref"),
                "requirement_id": p.get("requirement_id"),
            },
        )
        records.append(prec)
        seq += 1
        pc = p.get("payload_commitment")
        if isinstance(pc, str) and pc:
            checked = _sha256(p.get("payload", {}))
            if checked != pc:
                raise ImportContractError("proposal payload commitment mismatch")
            commitments.append(CommitmentRecord(
                label="payload_commitment", value=pc, algorithm="SHA-256",
                canonicalization_profile=CANONICAL_JSON_PROFILE,
                source_record_id=prec.record_id, source_path="proposal.payload_commitment",
                verification_status="checked_match",
            ))
    else:
        report.complete = False
        report.findings.append(ImportFinding(
            code="B002", category="missing_dependency", severity="warning", path="proposal",
            message="RuntimeProposal unavailable; correlation/profile provenance is unavailable.",
            value_state="unavailable",
        ))

    decisions: dict[str, dict[str, Any]] = {}
    bound_decision_ids: list[str] = []
    for i, raw in enumerate(cp["decisions"]):
        raw = _obj(raw, f"decisions[{i}]")
        did = raw.get("decision_id")
        if not isinstance(did, str) or not did:
            raise ImportContractError(f"decisions[{i}].decision_id required")
        _unique_or_same(decisions, did, raw, "decision_id")
        binding = raw.get("binding")
        ids = {"run_id": run_id, "decision_id": did, "effect_id": raw.get("effect_id")}
        if isinstance(binding, dict):
            ids.update({
                "manifest_id": binding.get("manifest_id"),
                "action_id": binding.get("action_id"),
                "grant_id": binding.get("grant_id"),
                "grant_revision": binding.get("grant_revision"),
                "authority_context_instance_id": binding.get("authority_context_id"),
                "requirement_id": binding.get("requirement_id"),
            })
        rec = _record(BOUNDED_PROFILE, "runtime_decision", seq, f"decisions[{i}]", raw,
                      ids=ids, at=raw.get("decided_at"))
        records.append(rec)
        seq += 1
        if isinstance(binding, dict):
            bound_decision_ids.append(did)
            if proposal is not None:
                _validate_proposal_binding(p, binding, f"decisions[{i}].binding")
            effect_id = raw.get("effect_id")
            expected = _sha256({
                "proposal": binding.get("proposal_commitment"),
                "grant_id": binding.get("grant_id"),
                "grant_revision": binding.get("grant_revision"),
            })
            if isinstance(effect_id, str) and effect_id != expected:
                raise ImportContractError(f"decision {did} has invalid effect identity")
            if isinstance(effect_id, str):
                commitments.append(CommitmentRecord(
                    label="effect_id", value=effect_id, algorithm="SHA-256",
                    canonicalization_profile=CANONICAL_JSON_PROFILE,
                    source_record_id=rec.record_id, source_path=f"decisions[{i}].effect_id",
                    verification_status="checked_match",
                    notes="Checked under pinned Control Plane effect-id contract.",
                ))
            for label in ("proposal_commitment", "manifest_digest", "payload_commitment",
                          "requirement_commitment", "role_mapping_digest"):
                value = binding.get(label)
                if isinstance(value, str) and value:
                    commitments.append(CommitmentRecord(
                        label=label, value=value,
                        algorithm="SHA-256" if value.startswith("sha256:") else "producer-declared",
                        canonicalization_profile=CANONICAL_JSON_PROFILE,
                        source_record_id=rec.record_id,
                        source_path=f"decisions[{i}].binding.{label}",
                        verification_status="attributed_claim",
                    ))

    if proposal is not None and len(bound_decision_ids) > 1:
        raise ImportContractError(
            "single-proposal importer does not support multiple authorization bindings"
        )
    if proposal is not None and not bound_decision_ids:
        report.complete = False
        report.findings.append(ImportFinding(
            code="B005", category="missing_dependency", severity="warning",
            path="decisions", message="Supplied proposal did not resolve to an authorization binding.",
            value_state="unavailable",
        ))

    decision_effects = {did: raw.get("effect_id") for did, raw in decisions.items()}
    known_effects = {value for value in decision_effects.values() if isinstance(value, str)}

    attempt_invariants: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(cp["attempts"]):
        raw = _obj(raw, f"attempts[{i}]")
        aid = raw.get("attempt_id")
        if not isinstance(aid, str) or not aid:
            raise ImportContractError(f"attempts[{i}].attempt_id required")
        did = raw.get("decision_id")
        eid = raw.get("effect_id")
        if did not in decision_effects:
            raise ImportContractError(f"attempts[{i}] has dangling decision_id {did}")
        if decision_effects[did] != eid:
            raise ImportContractError(f"attempts[{i}] effect_id does not match its decision")
        invariant = {k: raw.get(k) for k in ("attempt_id", "effect_id", "decision_id", "started_at")}
        _unique_or_same(attempt_invariants, aid, invariant, "attempt_id")
        records.append(_record(
            BOUNDED_PROFILE, "control_plane_attempt_transition", seq, f"attempts[{i}]", raw,
            ids={"run_id": run_id, "attempt_id": aid, "effect_id": raw.get("effect_id"),
                 "decision_id": raw.get("decision_id")},
            at=raw.get("started_at"),
        ))
        seq += 1

    for kind, field, time_field in (
        ("effect_observation", "observations", "observed_at"),
        ("reconciliation", "reconciliations", "reconciled_at"),
    ):
        for i, raw in enumerate(cp[field]):
            raw = _obj(raw, f"{field}[{i}]")
            eid = raw.get("effect_id")
            if eid not in known_effects:
                raise ImportContractError(f"{field}[{i}] has dangling effect_id {eid}")
            if field == "reconciliations":
                embedded = _obj(raw.get("observation"), f"{field}[{i}].observation")
                if embedded.get("effect_id") != eid:
                    raise ImportContractError(f"{field}[{i}].observation.effect_id conflicts with enclosing effect_id")
                if raw.get("result") == "applied" and embedded.get("state") != "applied":
                    raise ImportContractError(f"{field}[{i}] applied result conflicts with embedded observation")
                if raw.get("result") == "safe_to_retry" and embedded.get("state") != "absent":
                    raise ImportContractError(f"{field}[{i}] safe_to_retry conflicts with embedded observation")
            records.append(_record(
                BOUNDED_PROFILE, kind, seq, f"{field}[{i}]", raw,
                ids={"run_id": run_id, "effect_id": raw.get("effect_id")},
                at=raw.get(time_field),
            ))
            seq += 1

    if proposal is not None:
        profile_ref = proposal.get("authority_context_ref")
        instances = {
            d.get("binding", {}).get("authority_context_id")
            for d in cp["decisions"]
            if isinstance(d, dict) and isinstance(d.get("binding"), dict)
        }
        if profile_ref and profile_ref in instances:
            report.findings.append(ImportFinding(
                code="B003", category="conversion_warning", severity="warning",
                path="proposal.authority_context_ref",
                message="Profile reference equals a context-instance identifier; semantics remain distinct.",
            ))

    profiles = [ProducerProfile(
        profile_id=BOUNDED_PROFILE,
        producer="Cognous Agent Control Plane",
        repository="cogno-us/cognous-agent-control-plane",
        revision=CONTROL_PLANE_REVISION,
        format_name="BoundedRunRecord",
        format_version=None,
        notes="No embedded format version; adapter is revision-pinned.",
    )]

    moltbot_compatibility = None
    if moltbot_export is not None:
        source_export = _obj(moltbot_export, "moltbot_export")
        moltbot_compatibility = _resolve_moltbot_compatibility(source_export)
        mr, ml, mc, mf = _import_moltbot(
            source_export,
            seq,
            records,
            proposal=p if proposal is not None else None,
            producer_profile_id=moltbot_compatibility["profile_id"],
        )
        records.extend(mr); links.extend(ml); commitments.extend(mc); report.findings.extend(mf)
        profiles.append(ProducerProfile(
            profile_id=moltbot_compatibility["profile_id"],
            producer="Moltbot Safe",
            repository="cogno-us/moltbot-safe",
            revision=moltbot_compatibility["revision"],
            format_name=(
                "Executor producer evidence"
                if not moltbot_compatibility["legacy_unversioned"]
                else "ExecutionEnvelope + SQLite evidence"
            ),
            format_version=moltbot_compatibility["format_version"],
            notes=(
                "Source-asserted producer profile; synthetic local destination evidence; "
                "not independently established institutional verification."
                if not moltbot_compatibility["legacy_unversioned"]
                else "Legacy unversioned producer export; compatibility remains revision-pinned."
            ),
        ))
    else:
        report.complete = False
        report.findings.append(ImportFinding(
            code="B004", category="missing_dependency", severity="warning",
            path="moltbot_export", message="Executor/destination evidence absent.",
            value_state="absent",
        ))

    unresolved = any(
        r.record_type == "effect_observation" and r.data.get("state") in {"partial", "unknown"}
        for r in records
    )
    if unresolved:
        report.complete = False

    return ReconstructionBundle(
        run_id=run_id,
        status="reconstruction_complete" if report.complete else "reconstruction_partial",
        producer_profiles=profiles,
        records=records,
        links=links,
        commitments=commitments,
        import_reports=[report],
        semantics={
            "record_reconstruction": True,
            "policy_reevaluation": False,
            "model_reexecution": False,
            "external_effect_execution": False,
            "destination_observation": "producer_reported" if moltbot_export else "not_performed",
            "independent_effect_verification": False,
            "notes": "Replay reconstructs recorded events only; import never renews permission or creates an effect.",
        },
        metadata={
            "control_plane_revision": CONTROL_PLANE_REVISION,
            "moltbot_safe_revision": (
                moltbot_compatibility["revision"] if moltbot_compatibility else None
            ),
            "moltbot_producer_contract_version": (
                moltbot_compatibility["producer_contract_version"]
                if moltbot_compatibility else None
            ),
            "moltbot_repository_revision_provenance": (
                moltbot_compatibility["repository_revision_provenance"]
                if moltbot_compatibility else None
            ),
            "moltbot_revision_independently_established": (
                moltbot_compatibility["independently_established_provenance"]
                if moltbot_compatibility else None
            ),
            "moltbot_legacy_unversioned": (
                moltbot_compatibility["legacy_unversioned"]
                if moltbot_compatibility else None
            ),
            "manifest_revision": MANIFEST_REVISION,
            "alvorada_revision": ALVORADA_REVISION,
        },
    )


def _import_moltbot(
    source: dict[str, Any],
    seq: int,
    cp_records: list[SourceRecord],
    *,
    proposal: dict[str, Any] | None,
    producer_profile_id: str,
):
    source = _obj(source, "moltbot_export")
    required = {"execution_envelope", "execution_result", "effects", "attempts", "attempt_events"}
    missing = sorted(required - set(source))
    if missing:
        raise ImportContractError("Moltbot export missing: " + ",".join(missing))

    envelope = _obj(source["execution_envelope"], "execution_envelope")
    if envelope.get("version") != "0.2.0":
        raise ImportContractError("unsupported Moltbot ExecutionEnvelope version")
    op = _obj(envelope.get("operation"), "execution_envelope.operation")

    cp_decision_records = {
        r.identifiers.get("decision_id"): r
        for r in cp_records if r.record_type == "runtime_decision"
    }
    cp_decisions = {
        did: record.identifiers.get("effect_id")
        for did, record in cp_decision_records.items()
    }
    envelope_decision = envelope.get("decision_id")
    envelope_effect = envelope.get("effect_id")
    if envelope_decision not in cp_decisions:
        raise ImportContractError(f"Moltbot envelope has dangling decision_id {envelope_decision}")
    if cp_decisions[envelope_decision] != envelope_effect:
        raise ImportContractError("Moltbot envelope effect_id does not match Control Plane decision")
    decision_record = cp_decision_records[envelope_decision]
    binding = decision_record.data.get("binding")
    if not isinstance(binding, dict):
        raise ImportContractError("Moltbot envelope cannot bind to a Control Plane decision without authorization binding")
    if proposal is None:
        raise ImportContractError("Moltbot envelope requires the corresponding RuntimeProposal for cross-record validation")
    _validate_proposal_binding(proposal, binding, "decision.binding")
    _validate_envelope_chain(op, proposal, binding)
    expected_operation_digest = _sha256(op)

    records: list[SourceRecord] = []
    links: list[RecordLink] = []
    commitments: list[CommitmentRecord] = []
    findings: list[ImportFinding] = []

    er = _record(
        producer_profile_id, "execution_envelope", seq, "moltbot.execution_envelope", envelope,
        ids={
            "decision_id": envelope.get("decision_id"), "effect_id": envelope.get("effect_id"),
            "requested_attempt_id": envelope.get("attempt_id"),
            "manifest_id": op.get("manifest_id"), "action_id": op.get("action_id"),
            "grant_id": op.get("grant_id"), "grant_revision": op.get("grant_revision"),
            "authority_context_profile_ref": op.get("authority_context_id"),
            "institution_id": op.get("institution_id"), "authority_domain": op.get("authority_domain"),
        },
    )
    records.append(er); seq += 1
    pc = op.get("payload_commitment")
    if isinstance(pc, str):
        if _sha256(op.get("payload", {})) != pc:
            raise ImportContractError("Moltbot envelope payload commitment mismatch")
        commitments.append(CommitmentRecord(
            label="payload_commitment", value=pc, algorithm="SHA-256",
            canonicalization_profile=CANONICAL_JSON_PROFILE,
            source_record_id=er.record_id,
            source_path="moltbot.execution_envelope.operation.payload_commitment",
            verification_status="checked_match",
        ))

    result = _obj(source["execution_result"], "execution_result")
    if result.get("decision_id") != envelope_decision or result.get("effect_id") != envelope_effect:
        raise ImportContractError("Moltbot execution_result identifiers do not match execution envelope")
    result_observation = result.get("observation")
    if isinstance(result_observation, dict) and result_observation:
        _require_equal(result_observation.get("effect_id"), envelope_effect, "execution_result.observation.effect_id")
        if "state" in result_observation and result.get("observed_state") not in (None, "unknown"):
            _require_equal(result_observation.get("state"), result.get("observed_state"), "execution_result.observation.state")
        if "destination_state" in result_observation:
            _validate_observation_content(
                result_observation, envelope_effect, op, "execution_result.observation"
            )
    records.append(_record(
        producer_profile_id, "execution_result", seq, "moltbot.execution_result", result,
        ids={"decision_id": result.get("decision_id"), "effect_id": result.get("effect_id"),
             "attempt_id": result.get("attempt_id")},
    )); seq += 1

    attempts: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(source["attempts"]):
        raw = _obj(raw, f"moltbot.attempts[{i}]")
        aid = raw.get("attempt_id")
        if not isinstance(aid, str) or not aid:
            raise ImportContractError("Moltbot attempt missing attempt_id")
        if raw.get("decision_id") != envelope_decision or raw.get("effect_id") != envelope_effect:
            raise ImportContractError(f"Moltbot attempt {aid} does not match execution envelope")
        digest = raw.get("operation_digest")
        if digest not in (expected_operation_digest, "legacy:unknown"):
            raise ImportContractError(f"Moltbot attempt {aid} operation_digest mismatch")
        _unique_or_same(attempts, aid, raw, "Moltbot attempt_id")
        records.append(_record(
            producer_profile_id, "destination_attempt", seq, f"moltbot.attempts[{i}]", raw,
            ids={"attempt_id": aid, "effect_id": raw.get("effect_id"), "decision_id": raw.get("decision_id")},
        )); seq += 1

    for i, raw in enumerate(source["attempt_events"]):
        raw = _obj(raw, f"moltbot.attempt_events[{i}]")
        aid = raw.get("attempt_id")
        if aid not in attempts:
            raise ImportContractError(f"dangling Moltbot attempt event: {aid}")
        records.append(_record(
            producer_profile_id, "destination_attempt_event", seq, f"moltbot.attempt_events[{i}]", raw,
            ids={"attempt_id": aid, "event_id": raw.get("event_id"),
                 "effect_id": attempts[aid].get("effect_id"), "decision_id": attempts[aid].get("decision_id")},
        )); seq += 1

    result_attempt_id = result.get("attempt_id")
    if result_attempt_id is not None:
        if not isinstance(result_attempt_id, str) or not result_attempt_id:
            raise ImportContractError("execution_result.attempt_id must be a non-empty string when supplied")
        moltbot_ids = set(attempts)
        cp_attempt_ids = {
            r.identifiers.get("attempt_id")
            for r in cp_records if r.record_type == "control_plane_attempt_transition"
        }
        if result_attempt_id not in moltbot_ids and result_attempt_id not in cp_attempt_ids:
            raise ImportContractError(f"execution_result has dangling attempt_id {result_attempt_id}")
        if result_attempt_id in cp_attempt_ids and result_attempt_id not in moltbot_ids:
            if result.get("status") not in {"reconciled", "partial", "unknown"} or result.get("newly_executed") is not False:
                raise ImportContractError(
                    "Control Plane attempt namespace is valid only for non-new reconciliation results"
                )

    effects: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(source["effects"]):
        raw = _obj(raw, f"moltbot.effects[{i}]")
        eid = raw.get("effect_id")
        if not isinstance(eid, str) or not eid:
            raise ImportContractError("Moltbot effect missing effect_id")
        invariant = {k: raw.get(k) for k in
                     ("effect_id", "operation_digest", "grant_id", "target", "amount", "unit", "payload_json")}
        if eid != envelope_effect:
            raise ImportContractError("Moltbot effect_id does not match execution envelope")
        if raw.get("operation_digest") != expected_operation_digest:
            raise ImportContractError("Moltbot effect operation_digest mismatch")
        _require_equal(raw.get("grant_id"), op.get("grant_id"), f"moltbot.effects[{i}].grant_id")
        _require_equal(raw.get("target"), op.get("target"), f"moltbot.effects[{i}].target")
        _require_equal(raw.get("amount"), op.get("amount"), f"moltbot.effects[{i}].amount")
        _require_equal(raw.get("unit"), op.get("unit"), f"moltbot.effects[{i}].unit")
        _require_equal(
            _decode_payload_json(raw.get("payload_json"), f"moltbot.effects[{i}].payload_json"),
            op.get("payload"), f"moltbot.effects[{i}].payload_json",
        )
        _unique_or_same(effects, eid, invariant, "effect_id")
        rr = _record(
            producer_profile_id, "destination_effect", seq, f"moltbot.effects[{i}]", raw,
            ids={"effect_id": eid, "grant_id": raw.get("grant_id")},
        )
        records.append(rr); seq += 1
        digest = raw.get("operation_digest")
        if isinstance(digest, str):
            commitments.append(CommitmentRecord(
                label="operation_digest", value=digest, algorithm="SHA-256",
                canonicalization_profile=CANONICAL_JSON_PROFILE,
                source_record_id=rr.record_id, source_path=f"moltbot.effects[{i}].operation_digest",
                verification_status="checked_match",
                notes="Checked against the exact retained Execution Envelope operation under the pinned canonicalization profile.",
            ))

    cp_attempts = [r for r in cp_records if r.record_type == "control_plane_attempt_transition"]
    for cr in cp_attempts:
        ack = cr.data.get("acknowledgement")
        if isinstance(ack, dict) and isinstance(ack.get("attempt_id"), str):
            local_id = ack["attempt_id"]
            matches = [r for r in records
                       if r.record_type == "destination_attempt" and r.identifiers.get("attempt_id") == local_id]
            if len(matches) == 1:
                links.append(RecordLink(
                    link_type="explicit", from_record_id=cr.record_id, to_record_id=matches[0].record_id,
                    basis="Control Plane acknowledgement explicitly supplied Moltbot attempt_id.",
                    establishes_identity_equivalence=False,
                ))
            else:
                findings.append(ImportFinding(
                    code="M001", category="missing_dependency", severity="warning",
                    path=cr.source_path + ".acknowledgement.attempt_id",
                    message="Explicit executor attempt ID did not resolve uniquely.",
                    value_state="unavailable",
                ))

    if cp_attempts and attempts and not links:
        findings.append(ImportFinding(
            code="M002", category="unsupported_semantic", severity="warning",
            path="attempt_correlation",
            message="Control Plane and Moltbot attempt namespaces are preserved separately; no equivalence is inferred.",
            value_state="unknown",
        ))
    findings.append(ImportFinding(
        code="M003", category="conversion_warning", severity="info",
        path="moltbot.execution_envelope.operation.institution_id",
        message="Institution/domain provenance is the trusted Moltbot integration context, not Control Plane AuthorizationBinding.",
    ))
    findings.append(ImportFinding(
        code="M004", category="conversion_warning", severity="info",
        path="moltbot.execution_envelope.operation.authority_context_id",
        message="At the pinned adapter this field carries the proposal profile reference; it is distinct from the Control Plane binding context-instance ID.",
    ))
    return records, links, commitments, findings
