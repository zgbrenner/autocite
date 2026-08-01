from __future__ import annotations

import json
from pathlib import Path

import pytest

from autocite_mcp.retrieval import (
    DisabledEntityExtractor,
    LexicalRuleRetriever,
    RuleLibrary,
    RetrievalQuery,
    should_retrieve,
)


def test_builtin_library_has_licensed_stable_source_attributed_chunks():
    first = RuleLibrary.builtin()
    second = RuleLibrary.builtin()
    assert first.chunks
    assert [item.chunk_id for item in first.chunks] == [item.chunk_id for item in second.chunks]
    assert all(item.source_filename for item in first.chunks)
    assert all(item.heading for item in first.chunks)
    assert all(item.license for item in first.chunks)
    assert all(item.redistribution_allowed for item in first.chunks)


def test_unapproved_or_nonredistributable_material_is_excluded(tmp_path: Path):
    (tmp_path / "allowed.md").write_text("# Id.\nAn original summary.")
    (tmp_path / "blocked.md").write_text("# Proprietary\nExcluded text.")
    manifest = {
        "sources": [
            {"filename": "allowed.md", "included": True, "license": "CC0-1.0", "redistribution_allowed": True},
            {"filename": "blocked.md", "included": False, "license": "proprietary", "redistribution_allowed": False},
        ]
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    library = RuleLibrary.from_directory(tmp_path)
    assert {item.source_filename for item in library.chunks} == {"allowed.md"}


def test_metadata_filtering_precedes_small_top_k_ranking():
    library = RuleLibrary.builtin()
    retriever = LexicalRuleRetriever(library)
    results = retriever.retrieve(
        RetrievalQuery("ambiguous Id antecedent", mode="whitepages", rule_family="short_forms", source_type="case"),
        top_k=2,
    )
    assert 0 < len(results) <= 2
    assert all(item.chunk.mode in {"whitepages", "both"} for item in results)
    assert all(item.chunk.rule_family == "short_forms" for item in results)
    assert all(item.provenance == "retrieved_reference_material" for item in results)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"review_required": True},
        {"ambiguous_antecedent": True},
        {"mode_uncertain": True},
        {"uncommon_source_type": True},
        {"user_requested_explanation": True},
        {"model_lacks_context": True},
        {"confidence": 0.3},
    ],
)
def test_retrieval_triggers(kwargs):
    assert should_retrieve(**kwargs)


def test_clean_high_confidence_citation_does_not_trigger_retrieval():
    assert not should_retrieve(confidence=0.99)


def test_experimental_gliner_path_is_disabled_by_default():
    extractor = DisabledEntityExtractor()
    assert extractor.enabled is False
    assert extractor.extract("Jane Author, Useful Title") == []


def test_rule_index_round_trip_is_reproducible(tmp_path: Path):
    library = RuleLibrary.builtin()
    path = tmp_path / "index.json"
    library.save_index(path)
    first = path.read_bytes()
    library.save_index(path)
    assert path.read_bytes() == first
    assert RuleLibrary.load_index(path) == library


def test_local_passage_embedding_backend_reports_missing_optional_dependency(monkeypatch):
    import sys

    from autocite_mcp.retrieval import LocalPassageEmbeddingBackend

    # Force the ImportError branch regardless of whether the optional
    # 'retrieval' extra (sentence-transformers) happens to be installed in
    # this environment -- this test is specifically about that code path,
    # not about whatever the ambient environment has installed.
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    backend = LocalPassageEmbeddingBackend()
    with pytest.raises(RuntimeError, match="optional 'retrieval' dependencies"):
        backend.encode(["a", "b"])


def test_public_rule_context_returns_attributed_chunks():
    from autocite_mcp.tools import get_rule_context

    result = get_rule_context(
        "Id antecedent ambiguity",
        mode="bluepages",
        source_type="case",
        rule_family="short_forms",
    )
    assert result["local_only"] is True
    assert result["chunks"]
    assert result["chunks"][0]["chunk"]["source_filename"] == "short_forms.md"


@pytest.mark.parametrize(
    "rule_family",
    [
        "short forms: Id.",
        "short forms: cases",
        "short forms: statutes and regulations",
        "supra and hereinafter",
    ],
)
def test_rule_context_accepts_rule_spec_family_references(rule_family):
    # deterministic_rules.RULE_SPECS labels each rule with a fine-grained
    # rule_family_reference from a different vocabulary than the
    # reference_library manifest's three broad rule_family buckets -- a
    # caller who took rule_family_reference straight from a rule_findings
    # entry previously got silently zero results for this value.
    from autocite_mcp.tools import get_rule_context

    result = get_rule_context("Id antecedent ambiguity", rule_family=rule_family)
    assert result["chunks"]
    assert result["chunks"][0]["chunk"]["source_filename"] == "short_forms.md"


def test_rule_context_signal_family_aliases_map_to_signals_parentheticals():
    from autocite_mcp.tools import get_rule_context

    for rule_family in ("signals", "parentheticals", "citation groups and ordering"):
        result = get_rule_context("signal punctuation", rule_family=rule_family)
        assert result["chunks"], rule_family
        assert result["chunks"][0]["chunk"]["source_filename"] == "signals_parentheticals.md"


@pytest.mark.asyncio
async def test_review_shows_exact_local_chunks_and_clean_review_can_skip():
    from autocite_mcp.tools import review_document

    disputed = await review_document(
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020). Id. at 460.",
        apply_safe_fixes=False,
    )
    assert disputed["retrieval"]["triggered"] is True
    assert disputed["retrieval"]["chunks"]
    assert all(item["chunk"]["chunk_id"] for item in disputed["retrieval"]["chunks"])

    clean = await review_document(
        "See 42 U.S.C. § 1983.",
        mode="bluepages",
        apply_safe_fixes=False,
    )
    assert clean["retrieval"]["triggered"] is False
    assert clean["retrieval"]["chunks"] == []
