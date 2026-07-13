from autocite_mcp.knowledge import get_knowledge_pack, infer_citation_mode


def test_infer_mode_from_document_type():
    result = infer_citation_mode(document_type="law_review", text="")
    assert result["mode"] == "whitepages"
    assert result["confidence"] == "high"


def test_infer_mode_from_court_filing_text():
    result = infer_citation_mode(
        document_type="auto",
        text="IN THE UNITED STATES DISTRICT COURT\nCase No. 24-cv-100\nMotion to Dismiss",
    )
    assert result["mode"] == "bluepages"
    assert "court_filing_language" in result["signals"]


def test_knowledge_pack_is_compact_and_source_specific():
    pack = get_knowledge_pack("whitepages", ["case", "short_form", "internet"])
    assert pack["mode"] == "whitepages"
    assert set(pack["sources"]) == {"case", "short_form", "internet"}
    assert "never invent" in " ".join(pack["core_rules"]).lower()
    assert "archive" in " ".join(pack["sources"]["internet"]["checks"]).lower()


def test_unknown_guidance_source_fails_instead_of_silently_guessing():
    import pytest

    with pytest.raises(ValueError, match="Unknown source type"):
        get_knowledge_pack("bluepages", ["not-a-source"])


def test_knowledge_pack_includes_rule_families_and_cross_cutting_guidance():
    pack = get_knowledge_pack("bluepages", ["case", "short_form"])
    assert pack["sources"]["case"]["rule_family"] == "B10"
    assert pack["sources"]["short_form"]["rule_family"] == "B4"
    assert any("signal" in item.lower() for item in pack["general_guidance"])
    assert any("pincite" in item.lower() for item in pack["general_guidance"])
