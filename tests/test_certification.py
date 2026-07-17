import pytest

from autocite_mcp.certification import build_certification_report
from autocite_mcp.tools import generate_certification_report


@pytest.mark.asyncio
async def test_certification_report_from_local_review():
    text = "Smith v. Jones, 410 U.S. 113 (1973). Id. at 115. See 42 U.S.C. § 1983."
    report = await generate_certification_report(text)
    assert report["report_type"] == "citation_review_audit"
    assert report["citation_count"] >= 3
    assert report["verification_tier_counts"]["source_matched"] == 0
    assert any("not" in item.lower() for item in report["checks_not_performed"])
    assert "does not claim complete Bluebook compliance" in report["statement"]
    assert report["document_sha256"]
    assert "# Citation Review Audit Report" in report["markdown"]
    assert "410 U.S. 113" in report["markdown"]


@pytest.mark.asyncio
async def test_certification_never_marks_verified_without_verification():
    report = await generate_certification_report(
        "Roe v. Wade, 410 U.S. 113 (1973) supports this proposition."
    )
    assert all(
        entry["verification_tier"] == "mechanical_only" for entry in report["citations"]
    )
    assert any(
        "not_matched" not in entry["verification_tier"] for entry in report["citations"]
    )


def test_builder_reflects_verified_lookup_results():
    review = {
        "original_text": "Smith v. Jones, 410 U.S. 113 (1973).",
        "mode": "bluepages",
        "jurisdiction": "Federal",
        "citation_inventory": [
            {
                "text": "Smith v. Jones, 410 U.S. 113 (1973)",
                "source_type": "case",
                "start": 0,
                "end": 36,
            }
        ],
        "applied_edits": [],
        "remaining_issues": [],
        "case_verification": {
            "available": True,
            "results": [{"citation": "410 U.S. 113", "verified": True}],
        },
        "deep_review_results": {"available": False, "cases": []},
        "citation_graph": {"resolutions": []},
    }
    report = build_certification_report(review, prepared_for="Reviewing attorney")
    assert report["citations"][0]["verification_tier"] == "source_matched"
    assert report["verification_tier_counts"]["source_matched"] == 1
    assert report["prepared_for"] == "Reviewing attorney"
    assert any("CourtListener citation lookup" in item for item in report["checks_performed"])
