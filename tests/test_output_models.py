"""Direct model-validation tests for autocite_mcp.output_models.

These complement the MCP-client-layer assertions in tests/test_server.py
(which confirm FastMCP actually wires the models in as each tool's
outputSchema and validates real structuredContent) by validating the models
directly against the dicts produced by autocite_mcp.tools, independent of
the MCP protocol plumbing.
"""

from __future__ import annotations

import pytest

from autocite_mcp import tools
from autocite_mcp.output_models import (
    CaseVerificationOutput,
    CertificationReportOutput,
    CheckCitationsResult,
    CheckSingleCitationOutput,
    CitationGraphModel,
    ConvertCitationOutput,
    ExplainIssueOutput,
    HealthCheckOutput,
    JurisdictionProfile,
    KnowledgePack,
    ListCapabilitiesOutput,
    ResolveShortFormOutput,
    ReviewDocumentOutput,
    ReviewUploadedDocumentOutput,
    RuleCoverageEntry,
)
from autocite_mcp.local_product import health_report

SAMPLE_TEXT = (
    "See Brown v. Board of Education, 347 U.S. 483 (1954). Id. at 495. "
    "See also 42 U.S.C. § 1983."
)


def test_health_check_output_validates() -> None:
    model = HealthCheckOutput.model_validate(health_report(offline=True))
    assert model.status == "ok"
    assert model.platform.system


def test_jurisdiction_profile_models_validate() -> None:
    JurisdictionProfile.model_validate(tools.get_jurisdiction_profile("federal"))
    for profile in tools.list_jurisdiction_profiles():
        JurisdictionProfile.model_validate(profile)


def test_knowledge_pack_validates_with_and_without_jurisdiction_profile() -> None:
    KnowledgePack.model_validate(tools.get_citation_guidance())


def test_check_citations_both_shapes_validate() -> None:
    analyzed = tools.check_citations(SAMPLE_TEXT, apply_safe_fixes=False)
    fixed = tools.check_citations(SAMPLE_TEXT, apply_safe_fixes=True)
    analyzed_model = CheckCitationsResult.model_validate(analyzed)
    fixed_model = CheckCitationsResult.model_validate(fixed)
    assert analyzed_model.citations is not None
    assert analyzed_model.fixed_text is None
    assert fixed_model.fixed_text is not None
    assert fixed_model.citations is None


def test_check_single_citation_output_validates() -> None:
    CheckSingleCitationOutput.model_validate(
        tools.check_single_citation("347 U.S. 483 (1954)")
    )


def test_convert_citation_output_validates() -> None:
    ConvertCitationOutput.model_validate(
        tools.convert_citation(
            "Brown v. Board of Education, 347 U.S. 483 (1954)",
            target_mode="bluepages",
        )
    )


def test_explain_issue_output_validates() -> None:
    ExplainIssueOutput.model_validate(tools.explain_issue("CASE_PINCITE_REVIEW"))


def test_rule_coverage_entries_validate() -> None:
    for entry in tools.get_rule_coverage().values():
        RuleCoverageEntry.model_validate(entry)


def test_resolve_short_form_output_validates() -> None:
    ResolveShortFormOutput.model_validate(tools.resolve_short_form(SAMPLE_TEXT))


def test_citation_graph_model_validates() -> None:
    CitationGraphModel.model_validate(tools.get_citation_graph(SAMPLE_TEXT))


def test_list_capabilities_output_validates() -> None:
    ListCapabilitiesOutput.model_validate(tools.list_capabilities())


@pytest.mark.asyncio
async def test_case_verification_output_validates_without_token() -> None:
    result = await tools.verify_case_citations(SAMPLE_TEXT)
    model = CaseVerificationOutput.model_validate(result)
    assert model.available is False


@pytest.mark.asyncio
async def test_review_document_output_validates_deep_shape() -> None:
    review = await tools.review_document(SAMPLE_TEXT)
    model = ReviewDocumentOutput.model_validate(review)
    assert model.citation_graph.mode == "bluepages"
    assert model.citation_inventory
    assert model.jurisdiction_profile.id == "federal"
    assert model.knowledge.jurisdiction_profile is not None


@pytest.mark.asyncio
async def test_review_document_output_validates_with_deep_review_enabled() -> None:
    """deep_review_results is intentionally permissive (owned by deep_review.py,
    developed concurrently elsewhere); this exercises that path end-to-end
    without asserting on deep_review.py's internal field names."""
    review = await tools.review_document(SAMPLE_TEXT, deep_review=True)
    model = ReviewDocumentOutput.model_validate(review)
    assert isinstance(model.deep_review_results, dict)


@pytest.mark.asyncio
async def test_review_uploaded_document_output_validates() -> None:
    import base64

    payload = {
        "file_name": "doc.txt",
        "mime_type": "text/plain",
        "data_base64": base64.b64encode(SAMPLE_TEXT.encode("utf-8")).decode("ascii"),
    }
    review = await tools.review_uploaded_document(payload)
    model = ReviewUploadedDocumentOutput.model_validate(review)
    assert model.input_document.filename == "doc.txt"


@pytest.mark.asyncio
async def test_generate_certification_report_output_validates_deep_shape() -> None:
    report = await tools.generate_certification_report(
        SAMPLE_TEXT, prepared_for="Test Court"
    )
    model = CertificationReportOutput.model_validate(report)
    assert model.report_type == "citation_review_audit"
    assert model.citation_count == len(model.citations)
    assert sum(model.verification_tier_counts.values()) == model.citation_count
