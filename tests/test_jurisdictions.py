import pytest

from autocite_mcp.jurisdictions import (
    get_jurisdiction_profile,
    list_jurisdiction_profiles,
)


def test_curated_federal_and_california_profiles():
    federal = get_jurisdiction_profile("federal")
    california = get_jurisdiction_profile("CA")
    assert federal["verified_overrides"] is True
    assert california["id"] == "california"
    assert california["verified_overrides"] is True
    assert california["official_references"]


def test_all_states_are_addressable_with_safe_fallbacks():
    profiles = list_jurisdiction_profiles()
    postal_codes = {item["postal_code"] for item in profiles if item.get("postal_code")}
    assert len(postal_codes) == 50
    kansas = get_jurisdiction_profile("Kansas")
    assert kansas["id"] == "kansas"
    assert kansas["verified_overrides"] is False
    assert kansas["local_rule_review_required"] is True


def test_unknown_jurisdiction_is_rejected():
    with pytest.raises(ValueError, match="Unknown jurisdiction"):
        get_jurisdiction_profile("Atlantis")
