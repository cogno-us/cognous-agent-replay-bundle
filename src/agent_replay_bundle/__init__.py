"""Agent Replay Bundle - portable evidence package for AI-agent runs."""

from .loader import dump_replay_bundle, load_replay_bundle, load_replay_bundle_json
from .models import (
    ActionProposal,
    ActionType,
    AgentReplayBundle,
    AuthorityRecord,
    BlockedAction,
    BundleStatus,
    DecisionResult,
    PolicyDecision,
    PolicyEvaluationTrace,
    PolicyRuleEvaluation,
    RedactionMetadata,
    RelianceRecord,
    RunFrame,
    SignatureMetadata,
    SignedReplayBundle,
    SourceType,
    TraceRuleResult,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from .redaction import redact_replay_bundle
from .signing import (
    canonical_bundle_json,
    sign_replay_bundle,
    verify_signed_replay_bundle,
)
from .validator import validate_replay_bundle

__all__ = [
    "ActionProposal",
    "ActionType",
    "AgentReplayBundle",
    "AuthorityRecord",
    "BlockedAction",
    "BundleStatus",
    "DecisionResult",
    "PolicyDecision",
    "PolicyEvaluationTrace",
    "PolicyRuleEvaluation",
    "RedactionMetadata",
    "RelianceRecord",
    "RunFrame",
    "SignatureMetadata",
    "SignedReplayBundle",
    "SourceType",
    "TraceRuleResult",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "load_replay_bundle",
    "load_replay_bundle_json",
    "dump_replay_bundle",
    "validate_replay_bundle",
    "redact_replay_bundle",
    "canonical_bundle_json",
    "sign_replay_bundle",
    "verify_signed_replay_bundle",
]
