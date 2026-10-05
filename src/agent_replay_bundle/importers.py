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
MOLTBOT_SAFE_REVISION = "6b0ba1185bcd390f71df947dda349415e4105f5f"
MANIFEST_REVISION = "46c950bed37fe3812000895430bc0312d29e37ce"
ALVORADA_REVISION = "fb3d97938969a89e149e8ff8db2756091d1233fc"

LEGACY_PROFILE = "control-plane-legacy-replay@28350065"
BOUNDED_PROFILE = "control-plane-bounded-run@28350065"
MOLTBOT_PROFILE = "moltbot-safe-envelope-0.2.0@6b0ba118"


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

    attempt_invariants: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(cp["attempts"]):
        raw = _obj(raw, f"attempts[{i}]")
        aid = raw.get("attempt_id")
        if not isinstance(aid, str) or not aid:
            raise ImportContractError(f"attempts[{i}].attempt_id required")
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

    if moltbot_export is not None:
        mr, ml, mc, mf = _import_moltbot(moltbot_export, seq, records)
        records.extend(mr); links.extend(ml); commitments.extend(mc); report.findings.extend(mf)
        profiles.append(ProducerProfile(
            profile_id=MOLTBOT_PROFILE,
            producer="Moltbot Safe",
            repository="cogno-us/moltbot-safe",
            revision=MOLTBOT_SAFE_REVISION,
            format_name="ExecutionEnvelope + SQLite evidence",
            format_version="0.2.0",
            notes="Synthetic local destination evidence; not independent institutional verification.",
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
            "moltbot_safe_revision": MOLTBOT_SAFE_REVISION if moltbot_export else None,
            "manifest_revision": MANIFEST_REVISION,
            "alvorada_revision": ALVORADA_REVISION,
        },
    )


def _import_moltbot(source: dict[str, Any], seq: int, cp_records: list[SourceRecord]):
    source = _obj(source, "moltbot_export")
    required = {"execution_envelope", "execution_result", "effects", "attempts", "attempt_events"}
    missing = sorted(required - set(source))
    if missing:
        raise ImportContractError("Moltbot export missing: " + ",".join(missing))

    envelope = _obj(source["execution_envelope"], "execution_envelope")
    if envelope.get("version") != "0.2.0":
        raise ImportContractError("unsupported Moltbot ExecutionEnvelope version")
    op = _obj(envelope.get("operation"), "execution_envelope.operation")

    records: list[SourceRecord] = []
    links: list[RecordLink] = []
    commitments: list[CommitmentRecord] = []
    findings: list[ImportFinding] = []

    er = _record(
        MOLTBOT_PROFILE, "execution_envelope", seq, "moltbot.execution_envelope", envelope,
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
    records.append(_record(
        MOLTBOT_PROFILE, "execution_result", seq, "moltbot.execution_result", result,
        ids={"decision_id": result.get("decision_id"), "effect_id": result.get("effect_id"),
             "attempt_id": result.get("attempt_id")},
    )); seq += 1

    attempts: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(source["attempts"]):
        raw = _obj(raw, f"moltbot.attempts[{i}]")
        aid = raw.get("attempt_id")
        if not isinstance(aid, str) or not aid:
            raise ImportContractError("Moltbot attempt missing attempt_id")
        _unique_or_same(attempts, aid, raw, "Moltbot attempt_id")
        records.append(_record(
            MOLTBOT_PROFILE, "destination_attempt", seq, f"moltbot.attempts[{i}]", raw,
            ids={"attempt_id": aid, "effect_id": raw.get("effect_id"), "decision_id": raw.get("decision_id")},
        )); seq += 1

    for i, raw in enumerate(source["attempt_events"]):
        raw = _obj(raw, f"moltbot.attempt_events[{i}]")
        aid = raw.get("attempt_id")
        if aid not in attempts:
            raise ImportContractError(f"dangling Moltbot attempt event: {aid}")
        records.append(_record(
            MOLTBOT_PROFILE, "destination_attempt_event", seq, f"moltbot.attempt_events[{i}]", raw,
            ids={"attempt_id": aid, "event_id": raw.get("event_id"),
                 "effect_id": attempts[aid].get("effect_id"), "decision_id": attempts[aid].get("decision_id")},
        )); seq += 1

    effects: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(source["effects"]):
        raw = _obj(raw, f"moltbot.effects[{i}]")
        eid = raw.get("effect_id")
        if not isinstance(eid, str) or not eid:
            raise ImportContractError("Moltbot effect missing effect_id")
        invariant = {k: raw.get(k) for k in
                     ("effect_id", "operation_digest", "grant_id", "target", "amount", "unit", "payload_json")}
        _unique_or_same(effects, eid, invariant, "effect_id")
        rr = _record(
            MOLTBOT_PROFILE, "destination_effect", seq, f"moltbot.effects[{i}]", raw,
            ids={"effect_id": eid, "grant_id": raw.get("grant_id")},
        )
        records.append(rr); seq += 1
        digest = raw.get("operation_digest")
        if isinstance(digest, str):
            commitments.append(CommitmentRecord(
                label="operation_digest", value=digest, algorithm="SHA-256",
                canonicalization_profile=CANONICAL_JSON_PROFILE,
                source_record_id=rr.record_id, source_path=f"moltbot.effects[{i}].operation_digest",
                verification_status="attributed_claim",
                notes="Producer-stored digest; original operation remains separately retained.",
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
