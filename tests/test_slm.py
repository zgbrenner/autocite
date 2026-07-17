import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "src" / "autocite_mcp" / "slm.py"


def _load_slm():
    spec = importlib.util.spec_from_file_location("autocite_slm_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load SLM module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(**overrides):
    payload = {
        "citation_text": "42 USC §1983",
        "start": 4,
        "end": 16,
        "source_type": "statute",
        "mode": "bluepages",
        "issue_code": "STATUTE_CODE_ABBREVIATION",
        "explanation": "Normalize the code abbreviation and section spacing.",
        "confidence": "high",
        "proposed_citation": "42 U.S.C. § 1983",
        "missing_facts": [],
        "facts_used": {"title": "42", "section": "1983"},
        "antecedent_candidate": None,
        "abstain": False,
        "retrieved_rule_chunk_ids": [],
    }
    payload.update(overrides)
    return payload


def test_parses_strict_json_proposal():
    slm = _load_slm()
    proposal = slm.SLMProposal.from_json(json.dumps(_payload()))
    assert proposal.source_type == "statute"
    assert proposal.proposed_citation == "42 U.S.C. § 1983"
    assert proposal.abstain is False
    assert proposal.retrieved_rule_chunk_ids == ()


def test_normalizes_legacy_adapter_output_without_weakening_internal_schema():
    slm = _load_slm()
    payload = _payload()
    for key in ("antecedent_candidate", "abstain", "retrieved_rule_chunk_ids"):
        payload.pop(key)
    proposal = slm.CitationProposal.from_mapping(payload)
    assert proposal.abstain is False
    assert proposal.antecedent_candidate is None
    assert proposal.retrieved_rule_chunk_ids == ()


def test_rejects_inconsistent_abstention_contract():
    slm = _load_slm()
    with pytest.raises(ValueError, match="abstain"):
        slm.CitationProposal.from_mapping(_payload(abstain=True))


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        json.dumps({"citation_text": "42 USC §1983"}),
        json.dumps(_payload(confidence="certain")),
        json.dumps(_payload(mode="unknown")),
    ],
)
def test_rejects_malformed_or_invalid_contract(payload):
    slm = _load_slm()
    with pytest.raises(ValueError):
        slm.SLMProposal.from_json(payload)


def test_validates_exact_source_span_and_safe_normalization():
    slm = _load_slm()
    text = "See 42 USC §1983."
    proposal = slm.SLMProposal.from_mapping(_payload())
    result = slm.validate_proposal(
        proposal,
        text,
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    assert result.valid is True
    assert result.reasons == ()


def test_rejects_span_mismatch():
    slm = _load_slm()
    proposal = slm.SLMProposal.from_mapping(_payload(start=0, end=12))
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    assert result.valid is False
    assert "source_span_mismatch" in result.reasons


def test_rejects_offset_for_a_different_duplicate_citation():
    slm = _load_slm()
    text = "See 42 USC §1983; compare 42 USC §1983."
    proposal = slm.CitationProposal.from_mapping(_payload(start=27, end=39))
    result = slm.validate_proposal(
        proposal,
        text,
        expected_mode="bluepages",
        expected_source_type="statute",
        expected_start=4,
        expected_end=16,
    )
    assert "task_offset_mismatch" in result.reasons


def test_rejects_new_material_citation_facts():
    slm = _load_slm()
    proposal = slm.SLMProposal.from_mapping(
        _payload(proposed_citation="42 U.S.C. § 1983 (2024)")
    )
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    assert result.valid is False
    assert "unsupported_material_facts" in result.reasons


def test_rejects_claims_of_good_law_or_proposition_support():
    slm = _load_slm()
    proposal = slm.SLMProposal.from_mapping(
        _payload(explanation="This is good law and supports the proposition.")
    )
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    assert result.valid is False
    assert "prohibited_legal_claim" in result.reasons


def test_rejects_unknown_issue_code_and_unsupported_profile():
    slm = _load_slm()
    proposal = slm.CitationProposal.from_mapping(_payload(issue_code="MADE_UP_RULE"))
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        expected_source_type="statute",
        known_issue_codes={"STATUTE_CODE_ABBREVIATION"},
        supported_rule_profiles={"whitepages"},
    )
    assert "unknown_issue_code" in result.reasons
    assert "unsupported_rule_profile" in result.reasons


def test_rejects_low_confidence_missing_facts_and_deterministic_conflict():
    slm = _load_slm()
    proposal = slm.CitationProposal.from_mapping(
        _payload(confidence="low", missing_facts=["edition"])
    )
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        expected_source_type="statute",
        known_issue_codes={"STATUTE_CODE_ABBREVIATION"},
        deterministic_issues=[{"code": "REGULATION_CODE_ABBREVIATION"}],
    )
    assert "below_auto_action_threshold" in result.reasons
    assert "missing_required_facts" in result.reasons
    assert "deterministic_conflict" in result.reasons


def test_rejects_unattributed_retrieved_rule_chunk():
    slm = _load_slm()
    proposal = slm.CitationProposal.from_mapping(
        _payload(retrieved_rule_chunk_ids=["bluebook-summary:statutes"])
    )
    result = slm.validate_proposal(
        proposal,
        "See 42 USC §1983.",
        expected_mode="bluepages",
        supplied_rule_chunk_ids=set(),
    )
    assert "unattributed_rule_chunk" in result.reasons


def test_applies_only_valid_high_confidence_non_overlapping_proposals():
    slm = _load_slm()
    text = "See 42 USC §1983 and id."
    statute = slm.validate_proposal(
        slm.SLMProposal.from_mapping(_payload()),
        text,
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    low = slm.validate_proposal(
        slm.SLMProposal.from_mapping(
            _payload(
                citation_text="id.",
                start=21,
                end=24,
                source_type="short_form",
                issue_code="SHORT_FORM_CAPITALIZATION",
                confidence="low",
                proposed_citation="Id.",
                facts_used={},
            )
        ),
        text,
        expected_mode="bluepages",
        expected_source_type="short_form",
    )
    applied = slm.apply_validated_proposals(text, [statute, low])
    assert applied.text == "See 42 U.S.C. § 1983 and id."
    assert len(applied.applied) == 1
    assert len(applied.skipped) == 1
