import asyncio

import pytest

from autocite_mcp.slm_runtime import CallableSLMRuntime

from autocite_mcp.tools import (
    _CPU_BOUND_CONCURRENCY,
    check_citations,
    check_single_citation,
    convert_citation,
    explain_issue,
    get_citation_graph,
    get_citation_guidance,
    get_rule_context,
    list_capabilities,
    review_document,
    run_cpu_bound,
)


def test_check_single_citation_returns_focused_report():
    result = check_single_citation("42 USC §1983", mode="bluepages")
    assert result["citation"]["source_type"] == "statute"
    assert result["suggested_citation"] == "42 U.S.C. § 1983"


def test_check_single_citation_rejects_multiple_citations():
    with pytest.raises(ValueError, match="exactly one"):
        check_single_citation("42 U.S.C. § 1983 and 17 C.F.R. § 240.10b-5")


def test_convert_case_citation_to_bluepages_markdown():
    result = convert_citation(
        "Obergefell v. Hodges, 576 U.S. 644, 675 (2015)",
        target_mode="bluepages",
        output_style="markdown",
    )
    assert result["converted"] == "*Obergefell v. Hodges*, 576 U.S. 644, 675 (2015)"


def test_convert_state_statute_without_fabricating_title():
    result = convert_citation(
        "Mass. Gen. Laws ch. 1, § 2 (West 1999)",
        target_mode="whitepages",
    )
    assert result["converted"] == "Mass. Gen. Laws ch. 1, § 2 (West 1999)"


def test_convert_citation_never_leaks_internal_resolved_to_bookkeeping():
    # "resolved_to" is internal short-form-resolution bookkeeping (which
    # citation_graph authority a citation resolved to), not a citation fact.
    # Only the case branch used to strip it before returning facts_used;
    # every other source_type leaked it.
    for citation, mode in (
        ("42 U.S.C. § 1983 (2018)", "whitepages"),
        ("40 C.F.R. § 260.10 (2024)", "whitepages"),
        ("U.S. Const. amend. IV", "whitepages"),
    ):
        result = convert_citation(citation, target_mode=mode)
        assert "resolved_to" not in result["facts_used"], citation


def test_explain_issue_returns_mode_specific_rule():
    result = explain_issue("REPORTER_ABBREVIATION", mode="whitepages")
    assert result["rule"] == "Rule 10"


def test_explain_issue_covers_every_rule_findings_code():
    # rule_findings (review_document's contextual-rule output) is populated
    # exclusively from deterministic_rules.RULE_SPECS, a disjoint code
    # namespace from rules.RULE_CATALOG (the codes explain_issue previously
    # only recognized) -- a caller who saw one of these codes in
    # rule_findings and called explain_issue to learn more always got
    # "Unknown issue code". Every RULE_SPECS code must resolve.
    from autocite_mcp.deterministic_rules import RULE_SPECS

    for code in RULE_SPECS:
        result = explain_issue(code)
        assert result["code"] == code
        assert result["description"]
        assert result["rule"]


def test_explain_issue_rejects_unknown_code():
    with pytest.raises(ValueError, match="Unknown issue code"):
        explain_issue("NOT_A_REAL_CODE")


@pytest.mark.asyncio
async def test_review_document_rejects_none_text_with_valueerror_not_attributeerror():
    # A None text/citation/query argument previously crashed with an
    # unhandled AttributeError from `.strip()` deep inside each function,
    # rather than the same clean ValueError empty-string input already
    # gets. Only reachable via direct Python API use (the MCP tool-call
    # JSON schema boundary already rejects null), but local_product.py
    # documents that as a real, supported access path.
    with pytest.raises(ValueError, match="text must not be empty"):
        await review_document(None)


def test_check_citations_rejects_none_text_with_valueerror():
    with pytest.raises(ValueError, match="text must not be empty"):
        check_citations(None)


def test_get_citation_graph_rejects_none_text_with_valueerror():
    with pytest.raises(ValueError, match="text must not be empty"):
        get_citation_graph(None)


def test_get_rule_context_rejects_none_query_with_valueerror():
    with pytest.raises(ValueError, match="query must not be empty"):
        get_rule_context(None)


def test_check_single_citation_rejects_none_citation_with_valueerror():
    with pytest.raises(ValueError, match="citation must not be empty"):
        check_single_citation(None)


def test_convert_citation_rejects_none_citation_with_valueerror():
    with pytest.raises(ValueError, match="citation must not be empty"):
        convert_citation(None, target_mode="bluepages")


def test_explain_issue_rejects_none_code_with_valueerror():
    with pytest.raises(ValueError, match="Unknown issue code"):
        explain_issue(None)


def test_get_citation_guidance_treats_none_source_type_as_all():
    result = get_citation_guidance(source_type=None)
    assert result["sources"] == get_citation_guidance(source_type="all")["sources"]


@pytest.mark.asyncio
async def test_run_cpu_bound_caps_concurrent_thread_executions():
    # Without a cap, enough concurrent citation-dense requests could exhaust
    # the shared default thread pool that uploaded-document parsing,
    # desktop reads, and SLM generation also depend on. Verify the actual
    # number of simultaneous thread executions never exceeds the semaphore.
    import threading
    import time

    cap = _CPU_BOUND_CONCURRENCY._value
    lock = threading.Lock()
    current = 0
    peak = 0

    def slow_fn():
        nonlocal current, peak
        with lock:
            current += 1
            peak = max(peak, current)
        time.sleep(0.05)
        with lock:
            current -= 1

    await asyncio.gather(*[run_cpu_bound(slow_fn) for _ in range(cap * 3)])
    assert peak <= cap


def test_capabilities_disclose_verification_limits():
    result = list_capabilities()
    assert "case" in result["verification"]["courtlistener_supports"]
    assert "statutes" in result["verification"]["courtlistener_does_not_support"]


def test_check_citations_can_apply_safe_fixes():
    result = check_citations("42 USC §1983", mode="bluepages", apply_safe_fixes=True)
    assert result["fixed_text"] == "42 U.S.C. § 1983"
    assert result["applied_edits"][0]["correction_level"] == "safe_auto_fix"


@pytest.mark.asyncio
async def test_review_document_is_primary_model_friendly_workflow():
    from autocite_mcp.tools import review_document

    result = await review_document(
        "IN THE DISTRICT COURT\nSee 42 USC §1983. Id",
        document_type="auto",
        apply_safe_fixes=True,
    )
    assert result["mode_detection"]["mode"] == "bluepages"
    assert result["corrected_text"] == "IN THE DISTRICT COURT\nSee 42 U.S.C. § 1983. Id."
    assert result["knowledge"]["mode"] == "bluepages"
    assert result["response_contract"][0].startswith("Use corrected_text")
    assert result["mechanical_review_complete"] is True
    assert result["completion_scope"] == "detected citation-format issues only"
    assert result["slm_review"]["status"] == "not_requested"
    assert result["deterministic_edits"] == result["applied_edits"]
    assert result["remaining_deterministic_issues"] == result["remaining_issues"]
    assert result["model_proposals"] == []
    assert result["retrieved_guidance"] == result["retrieval"]["chunks"]
    assert result["retrieval"]["local_only"] is True
    assert result["source_verification_results"] == {
        "case_verification": result["case_verification"],
        "deep_review": result["deep_review_results"],
    }
    assert "rule_findings" in result
    assert set(result["correction_levels"]) == {
        "safe_auto_fix",
        "suggested_fix",
        "review_required",
        "unsupported",
    }


@pytest.mark.asyncio
async def test_review_document_slm_failure_preserves_deterministic_result():
    from autocite_mcp.tools import review_document

    result = await review_document(
        "See 42 USC §1983.",
        use_slm=True,
        _slm_runtime=CallableSLMRuntime(lambda prompt: "not json"),
    )
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["slm_review"]["status"] == "fallback"


@pytest.mark.asyncio
async def test_review_document_can_apply_validated_slm_fix_when_explicitly_enabled():
    import json

    from autocite_mcp.tools import review_document

    response = json.dumps(
        {
            "citation_text": "42 USC §1983",
            "start": 4,
            "end": 16,
            "source_type": "statute",
            "mode": "bluepages",
            "issue_code": "STATUTE_CODE_ABBREVIATION",
            "explanation": "Normalize abbreviation and spacing.",
            "confidence": "high",
            "proposed_citation": "42 U.S.C. § 1983",
            "missing_facts": [],
            "facts_used": {"title": "42", "section": "1983"},
        }
    )
    result = await review_document(
        "See 42 USC §1983.",
        apply_safe_fixes=False,
        use_slm=True,
        apply_slm_fixes=True,
        _slm_runtime=CallableSLMRuntime(lambda prompt: response),
    )
    assert result["corrected_text"] == "See 42 U.S.C. § 1983."
    assert result["slm_review"]["applied_count"] == 1


def test_get_citation_guidance_for_single_source():
    from autocite_mcp.tools import get_citation_guidance

    result = get_citation_guidance(mode="whitepages", source_type="journal_article")
    assert result["mode"] == "whitepages"
    assert set(result["sources"]) == {"journal_article"}


def test_empty_citation_inputs_raise_clean_validation_error():
    with pytest.raises(ValueError, match="citation must not be empty"):
        check_single_citation("", mode="bluepages")
    with pytest.raises(ValueError, match="citation must not be empty"):
        convert_citation("", target_mode="bluepages")


def test_convert_regulation_threads_or_requires_year():
    converted = convert_citation("40 C.F.R. § 260.10 (2024)", target_mode="whitepages")
    assert converted["converted"] == "40 C.F.R. § 260.10 (2024)"
    with pytest.raises(ValueError, match="year"):
        convert_citation("40 C.F.R. § 260.10", target_mode="whitepages")
