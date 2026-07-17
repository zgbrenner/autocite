"""Pydantic models for MCP tool `structuredContent`.

Why this module exists
-----------------------
Every ``@mcp.tool`` in ``server.py`` used to return ``dict[str, Any]`` (or
``list[dict[str, Any]]``). FastMCP's ``func_metadata`` (see
``mcp/server/fastmcp/utilities/func_metadata.py::_try_create_model_and_schema``)
still builds *some* output model for those annotations -- a ``RootModel``
wrapping ``dict[str, Any]`` -- but the resulting JSON Schema is just
``{"type": "object", "additionalProperties": true}``. Hosts get an
``outputSchema`` field, but it carries no information and enables no
``structuredContent`` validation.

``func_metadata`` treats a return annotation that is itself a ``BaseModel``
subclass specially (see ``_try_create_model_and_schema``, "Case 1"): the
model is used directly, and ``Tool.run(..., convert_result=True)`` ends up
calling ``FuncMetadata.convert_result``, which does::

    validated = self.output_model.model_validate(result)
    structured_content = validated.model_dump(mode="json", by_alias=True)

``result`` here is whatever the tool function returned -- we keep returning
plain dicts built by ``tools.py``, we only change the *return annotation*.
As long as the dict validates against the model, this produces a real
``outputSchema`` and a validated ``structuredContent`` block. The
*unstructured* ``content`` (the text block hosts have always parsed) is
computed from the raw, pre-validation ``result`` via
``_convert_to_content``/``pydantic_core.to_json`` and is completely
unaffected by any of this -- so existing text-based clients see byte-for-byte
the same thing they always have. Only the (newly populated) structured
content and the (newly informative) outputSchema change.

Modelling policy
-----------------
* Fields whose shape is fixed by first-party AutoCite code this change owns
  or that is stable and not concurrently under active development
  (``document_ir.py``, ``citation_graph.py``, ``engine.py``,
  ``certification.py``, ``verifiers.py``, ``knowledge.py``,
  ``jurisdictions.py``, ``deterministic_rules.py``, ``local_product.py``,
  ``workspace.py``) are modelled precisely, field-by-field, based on the
  actual dataclasses/dict literals in those modules.
* Fields sourced from modules that are being concurrently edited by another
  agent as part of this same change set (``retrieval.py``, ``deep_review.py``,
  ``evidence.py``, ``evaluation_framework.py``) are modelled only at the
  stable outer envelope this file constructs itself; their inner payloads
  stay ``dict[str, Any]`` / ``list[dict[str, Any]]`` so this module never
  fights a concurrent shape change with a spurious validation failure.
* Per-source-type citation ``components`` (case/statute/regulation/... each
  have different keys) are genuinely open-ended and stay ``dict[str, Any]``.
* All models inherit ``OutputModel`` (``extra="allow"``): an unexpected extra
  key in a validated dict is passed through to ``structuredContent`` rather
  than raising or being dropped, so structured content keeps parity with the
  unstructured text content and never turns a working tool call into an error.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class OutputModel(BaseModel):
    """Base for all tool output models.

    extra="allow" keeps structuredContent byte-parity with the unstructured text
    content: a field added to a tools.py payload before its model is updated
    passes through instead of being silently dropped from structuredContent.
    """

    model_config = ConfigDict(extra="allow")



# --------------------------------------------------------------------------
# Shared primitives
# --------------------------------------------------------------------------


class Citation(OutputModel):
    """One matched citation (``models.CitationMatch``)."""

    source_type: str
    text: str
    start: int
    end: int
    components: dict[str, Any] = {}


class CitationIssueModel(OutputModel):
    """A deterministic formatting issue (``models.CitationIssue``)."""

    code: str
    severity: str
    message: str
    rule: str
    start: int
    end: int
    original: str
    suggestion: str | None = None
    confidence: str = "medium"
    correction_level: str = "review_required"
    provenance: str = "deterministic_logic"


class RuleFindingModel(OutputModel):
    """A contextual rule finding (``deterministic_rules.RuleFinding``)."""

    issue_code: str
    family: str
    severity: str
    correction_level: str
    confidence: str
    start: int
    end: int
    original: str
    suggestion: str | None = None
    explanation: str
    rule_profile: str
    rule_family_reference: str
    required_facts: list[str] = []
    missing_facts: list[str] = []
    provenance: str = "deterministic_logic"


class AnalysisSummary(OutputModel):
    """``CitationEngine.analyze`` summary block."""

    citation_count: int
    issue_count: int
    autofixable_count: int
    by_source_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}


class JurisdictionProfile(OutputModel):
    """A jurisdiction profile (``jurisdictions._PROFILES`` entries).

    ``selected_mode``/``mode_note`` are only added by
    ``resolve_jurisdiction_profile`` (used inside ``review_document``); they
    stay optional so the same model also validates the plain
    ``get_jurisdiction_profile``/``list_jurisdiction_profiles`` output.
    """

    id: str
    display_name: str
    postal_code: str | None = None
    preferred_mode: str
    verified_overrides: bool
    local_rule_review_required: bool
    style_priority: str
    guidance: list[str] = []
    official_references: list[str] = []
    warning: str
    selected_mode: str | None = None
    mode_note: str | None = None


class ModeDetection(OutputModel):
    """``document_ir.classify_document_mode`` / ``knowledge.infer_citation_mode``."""

    selected_mode: str
    mode: str
    confidence: str
    evidence: list[str] = []
    signals: list[str] = []
    conflicting_evidence: list[str] = []
    user_confirmation_recommended: bool
    reason: str
    provenance: str = "deterministic_logic"


class CitationLocationModel(OutputModel):
    """``document_ir.CitationLocation``."""

    block_id: str | None = None
    block_kind: str | None = None
    absolute_start: int
    absolute_end: int
    block_local_start: int | None = None
    block_local_end: int | None = None
    note_id: str | None = None
    note_number: str | None = None
    page_number: int | None = None
    reconstruction_confidence: str = "certain"
    provenance: str = "parsed_document_structure"


class StructuredCitationOccurrence(OutputModel):
    """``document_ir.CitationOccurrence`` (structured_citation_inventory items)."""

    occurrence_id: str
    source_type: str
    text: str
    start: int
    end: int
    components: dict[str, Any] = {}
    location: CitationLocationModel


class DocumentIRSummary(OutputModel):
    """``document_ir.DocumentIR.summary()``."""

    source_format: str
    document_type: str
    mode: str | None = None
    block_count: int
    citation_count: int
    footnote_count: int
    endnote_count: int
    page_count: int
    warnings: list[str] = []


# --------------------------------------------------------------------------
# Citation graph (citation_graph.py dataclasses)
# --------------------------------------------------------------------------


class AuthorityNodeModel(OutputModel):
    authority_id: str
    source_type: str
    identity_key: list[str] = []
    display_name: str
    components: dict[str, Any] = {}
    identity_confidence: str
    provenance: str = "deterministic_logic"


class OccurrenceNodeModel(OutputModel):
    occurrence_id: str
    citation_text: str
    start: int
    end: int
    source_type: str
    form: str
    document_order: int
    location: CitationLocationModel
    components: dict[str, Any] = {}
    authority_id: str | None = None


class CitationEdgeModel(OutputModel):
    edge_type: str
    source_id: str
    target_id: str
    evidence: dict[str, Any] = {}
    provenance: str = "parsed_document_structure"


class AntecedentCandidateModel(OutputModel):
    authority_id: str
    occurrence_id: str
    score: int
    supporting_facts: list[str] = []
    disqualifying_facts: list[str] = []


class ResolutionResultModel(OutputModel):
    occurrence_id: str
    form: str
    resolved_authority_id: str | None = None
    resolution_method: str
    candidates: list[AntecedentCandidateModel] = []
    confidence: str
    disqualifying_facts: list[str] = []
    rule_profile: str
    human_review_required: bool
    provenance: str = "deterministic_logic"


class CitationGraphModel(OutputModel):
    """``citation_graph.CitationGraph.as_dict()``."""

    authorities: list[AuthorityNodeModel] = []
    occurrences: list[OccurrenceNodeModel] = []
    edges: list[CitationEdgeModel] = []
    resolutions: list[ResolutionResultModel] = []
    mode: str
    version: str = "1.0"


# --------------------------------------------------------------------------
# Knowledge / guidance (knowledge.py)
# --------------------------------------------------------------------------


class KnowledgeSourceGuidance(OutputModel):
    template: str
    required_facts: list[str] = []
    checks: list[str] = []
    rule_family: str


class ModeGuidanceModel(OutputModel):
    audience: str
    priorities: list[str] = []


class KnowledgePack(OutputModel):
    """``knowledge.get_knowledge_pack``.

    ``jurisdiction_profile`` is only stitched in by ``review_document``
    (``tools.py``: ``knowledge["jurisdiction_profile"] = profile``); the bare
    ``get_citation_guidance`` tool never sets it, hence the optional default.
    """

    mode: str
    core_rules: list[str] = []
    general_guidance: list[str] = []
    mode_guidance: ModeGuidanceModel
    sources: dict[str, KnowledgeSourceGuidance] = {}
    use: str
    jurisdiction_profile: JurisdictionProfile | None = None


# --------------------------------------------------------------------------
# Local-rule retrieval envelope (retrieval.py owns chunk internals; that
# module is under concurrent, active development elsewhere in this change
# set, so only the wrapper fields this file itself constructs are typed).
# --------------------------------------------------------------------------


class RuleRetrievalOutput(OutputModel):
    """``tools.get_rule_context``."""

    query: str
    backend: str
    local_only: bool
    chunks: list[dict[str, Any]] = []
    warning: str


class RetrievalMeta(OutputModel):
    """The ``retrieval`` block inside ``review_document``'s result."""

    triggered: bool
    backend: str
    local_only: bool
    chunks: list[dict[str, Any]] = []
    warning: str


# --------------------------------------------------------------------------
# CourtListener verification (verifiers.py)
# --------------------------------------------------------------------------


class CaseVerificationResult(OutputModel):
    citation: str | None = None
    normalized_citations: list[Any] = []
    start_index: int | None = None
    end_index: int | None = None
    status: int | None = None
    verified: bool = False
    ambiguous: bool = False
    error_message: str = ""
    case_names: list[str] = []
    urls: list[str] = []


class CaseVerificationOutput(OutputModel):
    """``verifiers.CourtListenerVerifier.verify_text`` / ``tools.verify_case_citations``."""

    available: bool
    reason: str | None = None
    message: str | None = None
    provider: str | None = None
    results: list[CaseVerificationResult] = []


# --------------------------------------------------------------------------
# Local SLM review envelope (slm_runtime.py: run_hybrid_review). Envelope
# fields are stable; individual proposal/rejection dict shapes vary by
# rejection reason, so they stay permissive.
# --------------------------------------------------------------------------


class SLMReviewModel(OutputModel):
    status: str
    model: str
    corrected_text: str
    suggestions: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    applied_count: int
    fallback_reason: str | None = None


class ModelProposalsModel(OutputModel):
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    deterministically_applied: list[dict[str, Any]] = []


class SourceVerificationResults(OutputModel):
    case_verification: CaseVerificationOutput
    deep_review: dict[str, Any] = {}


# --------------------------------------------------------------------------
# Health / local product (local_product.py)
# --------------------------------------------------------------------------


class PlatformInfo(OutputModel):
    system: str
    machine: str
    python: str


class PrivacyInfo(OutputModel):
    telemetry: bool
    document_logging: bool
    diagnostic_logging: str
    temporary_files: str
    cleanup: str


class NetworkInfo(OutputModel):
    review_default: str
    offline_enforced: bool
    capable_components: list[str] = []
    http_default_bind: str


class InstalledModel(OutputModel):
    model_id: str
    path: str
    size_bytes: int
    manifest_present: bool


class HealthCheckOutput(OutputModel):
    """``local_product.health_report`` / ``tools`` re-export via ``health_check``."""

    schema_version: str
    status: str
    service: str
    operating_modes: list[str] = []
    platform: PlatformInfo
    privacy: PrivacyInfo
    network: NetworkInfo
    installed_models: list[InstalledModel] = []
    offline_ready: bool
    deterministic_ready: bool
    local_ml_ready: bool


# --------------------------------------------------------------------------
# Certification report (certification.py -- fully deterministic, precise)
# --------------------------------------------------------------------------


class CertificationCitationEntry(OutputModel):
    citation: str | None = None
    source_type: str | None = None
    span: tuple[int | None, int | None] = (None, None)
    verification_tier: str


class CertificationReportOutput(OutputModel):
    """``certification.build_certification_report`` / ``generate_certification_report``."""

    schema_version: str
    report_type: str
    generated_at: str
    tool_version: str
    prepared_for: str | None = None
    document_sha256: str
    document_characters: int
    mode: str | None = None
    jurisdiction: str | None = None
    citation_count: int
    verification_tier_counts: dict[str, int] = {}
    verification_tier_legend: dict[str, str] = {}
    checks_performed: list[str] = []
    checks_not_performed: list[str] = []
    applied_edit_count: int
    outstanding_issue_count: int
    unresolved_short_form_count: int
    citations: list[CertificationCitationEntry] = []
    statement: str
    markdown: str


# --------------------------------------------------------------------------
# review_document / review_uploaded_document (tools.py)
# --------------------------------------------------------------------------


class ReviewDocumentOutput(OutputModel):
    """``tools.review_document`` / ``server.review_document``.

    ``deep_review_results`` stays a permissive ``dict[str, Any]``: it is
    produced by ``deep_review.py``, which is under concurrent, active
    development elsewhere in this change set, so this file intentionally does
    not couple to its internal field names.
    """

    schema_version: str
    workflow: str
    mode_detection: ModeDetection
    mode: str
    document_type: str
    jurisdiction: str
    jurisdiction_profile: JurisdictionProfile
    original_text: str
    corrected_text: str
    applied_edits: list[CitationIssueModel] = []
    deterministic_edits: list[CitationIssueModel] = []
    citation_inventory: list[Citation] = []
    structured_citation_inventory: list[StructuredCitationOccurrence] = []
    document_ir: DocumentIRSummary
    citation_graph: CitationGraphModel
    rule_findings: list[RuleFindingModel] = []
    correction_levels: dict[str, int] = {}
    initial_summary: AnalysisSummary
    final_summary: AnalysisSummary
    remaining_issues: list[CitationIssueModel] = []
    remaining_deterministic_issues: list[CitationIssueModel] = []
    mechanical_review_complete: bool
    completion_scope: str
    knowledge: KnowledgePack
    case_verification: CaseVerificationOutput
    deep_review_results: dict[str, Any] = {}
    slm_review: SLMReviewModel
    model_proposals: ModelProposalsModel | list[Any] = []
    retrieved_guidance: list[dict[str, Any]] = []
    retrieval: RetrievalMeta
    source_verification_results: SourceVerificationResults
    confidence_legend: dict[str, str] = {}
    response_contract: list[str] = []


class InputDocumentInfo(OutputModel):
    """``tools.review_uploaded_document``'s appended ``input_document`` block."""

    filename: str
    mime_type: str | None = None
    source_format: str
    warnings: list[str] = []
    sha256: str
    document_ir: DocumentIRSummary | None = None


class ReviewUploadedDocumentOutput(ReviewDocumentOutput):
    """``tools.review_uploaded_document``: a full review plus ``input_document``."""

    input_document: InputDocumentInfo


# --------------------------------------------------------------------------
# open_citecheck_workspace (workspace.py + server.py)
# --------------------------------------------------------------------------


class WorkspaceSummary(OutputModel):
    mode: str | None = None
    applied_edit_count: int
    remaining_issue_count: int
    deep_case_count: int


class OpenCitecheckWorkspaceOutput(OutputModel):
    """``workspace.workspace_payload`` plus the ``message`` key ``server.py`` adds."""

    summary: WorkspaceSummary
    original_text: str
    corrected_text: str
    issues: list[CitationIssueModel] = []
    applied_edits: list[CitationIssueModel] = []
    deep_review_results: dict[str, Any] = {}
    response_contract: list[str] = []
    message: str


# --------------------------------------------------------------------------
# export_review_docx (documents.py + tools.py)
# --------------------------------------------------------------------------


class ExportReviewDocxOutput(OutputModel):
    filename: str
    mime_type: str
    data_base64: str
    sha256: str
    size_bytes: int
    tracked_changes: bool
    limitations: list[str] = []


# --------------------------------------------------------------------------
# Small, single-purpose tool outputs (tools.py)
# --------------------------------------------------------------------------


class CheckCitationsResult(OutputModel):
    """``tools.check_citations`` / ``fix_citations``.

    ``CitationEngine.analyze`` and ``CitationEngine.fix`` return two
    genuinely different shapes selected at call time by the caller-supplied
    ``apply_safe_fixes`` flag (``check_citations`` exposes that flag
    directly), so every field beyond ``mode`` is optional and ``summary``
    stays a permissive dict (its value types differ between the two shapes:
    plain counts for the fix summary, nested per-category count dicts for
    the analyze summary).
    """

    mode: str
    # `apply_safe_fixes=False` (analyze) shape:
    citations: list[Citation] | None = None
    issues: list[CitationIssueModel] | None = None
    limitations: list[str] | None = None
    # `apply_safe_fixes=True` (fix) shape:
    original_text: str | None = None
    fixed_text: str | None = None
    applied_edits: list[CitationIssueModel] | None = None
    remaining_issues: list[CitationIssueModel] | None = None
    summary: dict[str, Any] = {}


class ResolveShortFormOutput(OutputModel):
    schema_version: str
    mode: str
    resolutions: list[ResolutionResultModel] = []


class RuleCoverageEntry(OutputModel):
    status: str
    implemented_rules: list[str] = []
    claim: str


class CheckSingleCitationOutput(OutputModel):
    mode: str
    citation: Citation
    issues: list[CitationIssueModel] = []
    suggested_citation: str
    remaining_issues: list[CitationIssueModel] = []


class ConvertCitationOutput(OutputModel):
    source_type: str
    target_mode: str
    output_style: str
    original: str
    converted: str
    facts_used: dict[str, Any] = {}


class GenerateCitationOutput(OutputModel):
    """``server.generate_citation`` (the only tool built directly in server.py)."""

    source_type: str
    mode: str
    output_style: str
    citation: str
    facts_used: dict[str, Any] = {}


class ExplainIssueOutput(OutputModel):
    code: str
    title: str
    description: str
    severity: str
    autofix: bool
    mode: str
    rule: str


# --------------------------------------------------------------------------
# list_capabilities (tools.py) -- a hand-authored capability manifest.
# --------------------------------------------------------------------------


class LocalSlmCapability(OutputModel):
    available: bool
    optional: bool
    default_model: str
    default_behavior: str
    applies_edits_only_when: str
    fallback: str
    never_claims: list[str] = []


class DeepReviewCapability(OutputModel):
    available: bool
    provider: str
    features: list[str] = []
    never_claims: list[str] = []


class DocumentAnalysisCapability(OutputModel):
    extracts: list[str] = []
    parser: str
    short_form_resolution: str
    safe_autofixes: list[str] = []


class VerificationCapability(OutputModel):
    provider: str
    courtlistener_supports: list[str] = []
    courtlistener_does_not_support: list[str] = []
    requires_environment_variable: str


class ListCapabilitiesOutput(OutputModel):
    primary_workflow: str
    automatic_mode_detection: bool
    local_slm: LocalSlmCapability
    deep_review: DeepReviewCapability
    document_formats: list[str] = []
    document_exports: list[str] = []
    jurisdiction_profiles: int
    modes: list[str] = []
    source_types: list[str] = []
    document_analysis: DocumentAnalysisCapability
    verification: VerificationCapability
    guardrails: list[str] = []
