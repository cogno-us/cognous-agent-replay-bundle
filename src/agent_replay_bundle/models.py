"""Pydantic models for Agent Replay Bundle."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """The category of action an agent proposed."""

    read = "read"
    write = "write"
    external_send = "external_send"
    delete = "delete"
    export = "export"
    purchase = "purchase"
    approve = "approve"
    escalate = "escalate"
    other = "other"


class DecisionResult(str, Enum):
    """The outcome of a policy decision."""

    allow = "allow"
    block = "block"
    escalate = "escalate"


class TraceRuleResult(str, Enum):
    """The result of a single policy rule evaluation within a trace."""

    allow = "allow"
    block = "block"
    escalate = "escalate"
    none = "none"


class SourceType(str, Enum):
    """The type of source referenced by a reliance record."""

    tool = "tool"
    database = "database"
    file = "file"
    api = "api"
    user_input = "user_input"
    model_output = "model_output"
    other = "other"


class ValidationSeverity(str, Enum):
    """Severity level of a validation issue."""

    error = "error"
    warning = "warning"


class BundleStatus(str, Enum):
    """The completion or redaction status of the bundle."""

    complete = "complete"
    partial = "partial"
    redacted = "redacted"


class RunFrame(BaseModel):
    """The task frame that describes the agent run context."""

    frame_id: str = Field(description="Unique identifier for this run frame.")
    task: str = Field(description="The task or goal the agent was given.")
    actor: str = Field(description="The agent or system performing the run.")
    environment: str = Field(description="The environment in which the run occurred (e.g. production, staging).")
    allowed_tools: list[str] = Field(default_factory=list, description="Tools the agent was permitted to use.")
    blocked_tools: list[str] = Field(default_factory=list, description="Tools the agent was explicitly prohibited from using.")
    policy_version: str = Field(description="The version of the policy set applied during the run.")
    created_at: str = Field(description="ISO 8601 timestamp when the frame was created.")


class ActionProposal(BaseModel):
    """A single action proposed by the agent during the run."""

    action_id: str = Field(description="Unique identifier for this action proposal.")
    run_id: str = Field(description="The run this proposal belongs to.")
    tool_name: str = Field(description="The tool the agent proposed to invoke.")
    action_type: ActionType = Field(description="Category of action being proposed.")
    target: str = Field(description="The resource or endpoint the action targets.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Parameters or data the action would send.")
    proposed_at: str = Field(description="ISO 8601 timestamp when the proposal was generated.")
    reason: str | None = Field(default=None, description="The agent's stated reason for proposing this action.")


class PolicyDecision(BaseModel):
    """A policy decision made in response to an action proposal."""

    decision_id: str = Field(description="Unique identifier for this policy decision.")
    action_id: str = Field(description="The action proposal this decision applies to.")
    run_id: str = Field(description="The run this decision belongs to.")
    result: DecisionResult = Field(description="The outcome of the policy evaluation (allow, block, escalate).")
    policy_name: str = Field(description="Name of the policy that produced this decision.")
    reason: str = Field(description="Human-readable explanation of why this decision was made.")
    decided_at: str = Field(description="ISO 8601 timestamp when the decision was made.")
    deterministic_fingerprint: str = Field(description="A stable hash of the policy inputs, used for integrity verification.")
    trace_id: str | None = Field(default=None, description="Optional reference to the PolicyEvaluationTrace for this decision.")


class PolicyRuleEvaluation(BaseModel):
    """The result of evaluating a single policy rule within a trace."""

    rule_name: str = Field(description="Name of the policy rule that was evaluated.")
    matched: bool = Field(description="Whether the rule matched the action proposal.")
    result: TraceRuleResult = Field(description="The result produced by this rule (allow, block, escalate, none).")
    reason: str = Field(description="Explanation of why the rule produced this result.")


class PolicyEvaluationTrace(BaseModel):
    """A detailed trace of the policy evaluation process for an action proposal."""

    trace_id: str = Field(description="Unique identifier for this evaluation trace.")
    run_id: str = Field(description="The run this trace belongs to.")
    action_id: str = Field(description="The action proposal this trace covers.")
    evaluated_at: str = Field(description="ISO 8601 timestamp when the evaluation occurred.")
    rules_evaluated: list[PolicyRuleEvaluation] = Field(default_factory=list, description="Individual rule evaluations that contributed to the final result.")
    final_result: DecisionResult = Field(description="The final policy decision produced by this trace.")
    deterministic_fingerprint: str = Field(description="A stable hash of the evaluation inputs, matching the corresponding PolicyDecision.")


class BlockedAction(BaseModel):
    """A record of an action that was blocked by policy."""

    blocked_id: str = Field(description="Unique identifier for this blocked action record.")
    action_id: str = Field(description="The action proposal that was blocked.")
    run_id: str = Field(description="The run this blocked action belongs to.")
    reason: str = Field(description="The reason the action was blocked.")
    policy_name: str = Field(description="The policy that blocked the action.")
    blocked_at: str = Field(description="ISO 8601 timestamp when the action was blocked.")


class AuthorityRecord(BaseModel):
    """A record of authority granted to the actor for this run."""

    authority_id: str = Field(description="Unique identifier for this authority record.")
    run_id: str = Field(description="The run this authority record applies to.")
    actor: str = Field(description="The agent or principal that holds this authority.")
    scope: list[str] = Field(description="The list of permissions or capabilities covered by this authority.")
    source: str = Field(description="Where the authority originated (e.g. user delegation, system policy).")
    expires_at: str | None = Field(default=None, description="Optional ISO 8601 timestamp when this authority expires.")
    created_at: str = Field(description="ISO 8601 timestamp when the authority was granted.")


class RelianceRecord(BaseModel):
    """A record of a data source the agent relied on during the run."""

    reliance_id: str = Field(description="Unique identifier for this reliance record.")
    run_id: str = Field(description="The run this reliance record belongs to.")
    source_name: str = Field(description="Name of the data source that was consulted.")
    source_type: SourceType = Field(description="Category of the data source (tool, database, file, api, etc.).")
    scope: str = Field(description="Description of what aspect of the source was relied upon.")
    referenced_action_id: str | None = Field(default=None, description="Optional reference to the action proposal that triggered this reliance.")
    created_at: str = Field(description="ISO 8601 timestamp when the reliance was recorded.")


class ValidationIssue(BaseModel):
    """A single issue found during bundle validation."""

    severity: ValidationSeverity = Field(description="Whether this issue is an error or a warning.")
    code: str = Field(description="A stable code string identifying the type of issue.")
    message: str = Field(description="Human-readable description of the issue.")
    path: str | None = Field(default=None, description="Optional dot-path to the field or object that triggered this issue.")


class ValidationReport(BaseModel):
    """The result of validating an AgentReplayBundle."""

    valid: bool = Field(description="True only when no error-severity issues were found.")
    checked_object_type: str = Field(default="AgentReplayBundle", description="The type of object that was validated.")
    checked_id: str = Field(description="The bundle_id (or signed_bundle_id) of the validated object.")
    issues: list[ValidationIssue] = Field(default_factory=list, description="List of validation issues found (errors and warnings).")


class RedactionMetadata(BaseModel):
    """Metadata describing what was redacted from the bundle."""

    redacted: bool = Field(default=False, description="Whether any redaction has been applied to this bundle.")
    redacted_at: str | None = Field(default=None, description="ISO 8601 timestamp when redaction was performed.")
    redacted_fields: list[str] = Field(default_factory=list, description="List of field paths that were redacted.")
    redaction_policy: str | None = Field(default=None, description="Name or identifier of the redaction policy applied.")
    replacement: str = Field(default="[REDACTED]", description="The placeholder value used to replace redacted content.")
    notes: str | None = Field(default=None, description="Optional human-readable notes about the redaction.")


class SignatureMetadata(BaseModel):
    """Metadata describing an export integrity signature applied to the bundle."""

    signed: bool = Field(default=False, description="Whether this bundle has been signed.")
    signed_at: str | None = Field(default=None, description="ISO 8601 timestamp when the signature was applied.")
    signature_algorithm: str | None = Field(default=None, description="The algorithm used to produce the signature (e.g. HMAC-SHA256).")
    signature: str | None = Field(default=None, description="The hex-encoded signature value.")
    key_id: str | None = Field(default=None, description="Optional identifier for the signing key used.")


class AgentReplayBundle(BaseModel):
    """A portable evidence package for a completed or partially completed AI-agent run."""

    bundle_id: str = Field(description="Unique identifier for this replay bundle.")
    bundle_version: str = Field(default="0.1", description="Version of the replay bundle format.")
    run_id: str = Field(description="Unique identifier for the agent run this bundle covers.")
    status: BundleStatus = Field(default=BundleStatus.complete, description="Completion or redaction status of the bundle.")
    generated_at: str = Field(description="ISO 8601 timestamp when this bundle was generated.")
    producer: str | None = Field(default=None, description="Optional identifier of the system or component that produced this bundle.")
    frame: RunFrame = Field(description="The task frame describing the run context.")
    action_proposals: list[ActionProposal] = Field(default_factory=list, description="All action proposals made by the agent during the run.")
    policy_decisions: list[PolicyDecision] = Field(default_factory=list, description="All policy decisions made in response to action proposals.")
    policy_traces: list[PolicyEvaluationTrace] = Field(default_factory=list, description="Detailed policy evaluation traces for action proposals.")
    blocked_actions: list[BlockedAction] = Field(default_factory=list, description="Records of actions that were blocked by policy.")
    authority_records: list[AuthorityRecord] = Field(default_factory=list, description="Authority grants in scope for this run.")
    reliance_records: list[RelianceRecord] = Field(default_factory=list, description="Data sources the agent relied on during the run.")
    final_output: str | None = Field(default=None, description="The final output produced by the agent run, if available.")
    validation_report: ValidationReport | None = Field(default=None, description="An embedded validation report for this bundle, if generated.")
    redaction_metadata: RedactionMetadata | None = Field(default=None, description="Metadata describing any redaction applied to this bundle.")
    signature_metadata: SignatureMetadata | None = Field(default=None, description="Metadata describing any export integrity signature applied.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary additional metadata about the bundle.")


class SignedReplayBundle(BaseModel):
    """A replay bundle paired with its export integrity signature."""

    signed_bundle_id: str = Field(description="Unique identifier for this signed bundle.")
    replay_bundle: AgentReplayBundle = Field(description="The underlying replay bundle.")
    signature_metadata: SignatureMetadata = Field(description="The signature applied to the replay bundle.")
