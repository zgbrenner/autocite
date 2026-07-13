from __future__ import annotations

from typing import Any

_STATE_PAIRS = [
    ("Alabama", "AL"), ("Alaska", "AK"), ("Arizona", "AZ"), ("Arkansas", "AR"),
    ("California", "CA"), ("Colorado", "CO"), ("Connecticut", "CT"), ("Delaware", "DE"),
    ("Florida", "FL"), ("Georgia", "GA"), ("Hawaii", "HI"), ("Idaho", "ID"),
    ("Illinois", "IL"), ("Indiana", "IN"), ("Iowa", "IA"), ("Kansas", "KS"),
    ("Kentucky", "KY"), ("Louisiana", "LA"), ("Maine", "ME"), ("Maryland", "MD"),
    ("Massachusetts", "MA"), ("Michigan", "MI"), ("Minnesota", "MN"), ("Mississippi", "MS"),
    ("Missouri", "MO"), ("Montana", "MT"), ("Nebraska", "NE"), ("Nevada", "NV"),
    ("New Hampshire", "NH"), ("New Jersey", "NJ"), ("New Mexico", "NM"), ("New York", "NY"),
    ("North Carolina", "NC"), ("North Dakota", "ND"), ("Ohio", "OH"), ("Oklahoma", "OK"),
    ("Oregon", "OR"), ("Pennsylvania", "PA"), ("Rhode Island", "RI"), ("South Carolina", "SC"),
    ("South Dakota", "SD"), ("Tennessee", "TN"), ("Texas", "TX"), ("Utah", "UT"),
    ("Vermont", "VT"), ("Virginia", "VA"), ("Washington", "WA"), ("West Virginia", "WV"),
    ("Wisconsin", "WI"), ("Wyoming", "WY"),
]


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def _generic_state(name: str, postal_code: str) -> dict[str, Any]:
    return {
        "id": _slug(name),
        "display_name": name,
        "postal_code": postal_code,
        "preferred_mode": "bluepages",
        "verified_overrides": False,
        "local_rule_review_required": True,
        "style_priority": (
            f"For filings in {name}, controlling court rules and any official state citation manual "
            "take priority over general Bluepages guidance."
        ),
        "guidance": [
            "Confirm the court's current local rules and judge-specific requirements.",
            "Confirm preferred state reporters, code editions, administrative sources, and public-domain formats.",
            "Do not infer state-specific abbreviations or parallel-citation requirements from another jurisdiction.",
        ],
        "official_references": [],
        "warning": "AutoCite identifies this jurisdiction but has not encoded verified jurisdiction-specific overrides.",
    }


_PROFILES: dict[str, dict[str, Any]] = {
    "federal": {
        "id": "federal",
        "display_name": "United States Federal Courts",
        "postal_code": None,
        "preferred_mode": "bluepages",
        "verified_overrides": True,
        "local_rule_review_required": True,
        "style_priority": "The filing court's Federal Rules, circuit/district local rules, and judge-specific orders control over general citation guidance.",
        "guidance": [
            "Confirm whether the court requires record citations, ECF references, appendices, or special short forms.",
            "Use the deciding court and year when the reporter does not uniquely identify the court.",
            "Treat unpublished, slip, database, and administrative authorities according to the filing court's rules.",
        ],
        "official_references": [
            "https://www.uscourts.gov/court-records/find-case-pacer/court-links",
            "https://www.uscourts.gov/forms-rules/current-rules-practice-procedure",
        ],
        "warning": "Federal local rules differ by court and remain a source-review requirement.",
    }
}

for _name, _postal in _STATE_PAIRS:
    _PROFILES[_slug(_name)] = _generic_state(_name, _postal)

_PROFILES["california"] = {
    "id": "california",
    "display_name": "California",
    "postal_code": "CA",
    "preferred_mode": "bluepages",
    "verified_overrides": True,
    "local_rule_review_required": True,
    "style_priority": "For California court filings, current California Rules of Court, local rules, and the California Style Manual take priority over general Bluepages conventions.",
    "guidance": [
        "Confirm California public-domain and official-reporter formats for the court and document type.",
        "Use California statutory and regulatory source names and abbreviations rather than federal analogues.",
        "Review local rules and standing orders for record, exhibit, and electronic-docket citations.",
        "Academic writing may still require Whitepages mode even when the subject matter is California law.",
    ],
    "official_references": [
        "https://courts.ca.gov/cms/rules/index",
        "https://courts.ca.gov/cms/rules/local-rules-court",
    ],
    "warning": "AutoCite provides a curated priority profile, not a substitute for the current California Style Manual or filing court rules.",
}

_ALIASES: dict[str, str] = {
    "us": "federal",
    "u.s.": "federal",
    "united_states": "federal",
    "federal_court": "federal",
}
for _name, _postal in _STATE_PAIRS:
    _id = _slug(_name)
    _ALIASES[_name.lower()] = _id
    _ALIASES[_name.lower().replace(" ", "_")] = _id
    _ALIASES[_postal.lower()] = _id


def get_jurisdiction_profile(identifier: str | None) -> dict[str, Any]:
    if identifier is None or not str(identifier).strip() or str(identifier).strip().lower() in {
        "auto", "unspecified", "unknown"
    }:
        return dict(_PROFILES["federal"])
    key = str(identifier).strip().lower().replace("-", "_")
    key = _ALIASES.get(key, key)
    profile = _PROFILES.get(key)
    if profile is None:
        raise ValueError(f"Unknown jurisdiction profile: {identifier}")
    return dict(profile)


def list_jurisdiction_profiles() -> list[dict[str, Any]]:
    return [dict(_PROFILES[key]) for key in sorted(_PROFILES)]


def resolve_jurisdiction_profile(identifier: str | None, mode: str) -> dict[str, Any]:
    profile = get_jurisdiction_profile(identifier)
    profile["selected_mode"] = mode
    if mode == "whitepages":
        profile["mode_note"] = (
            "Whitepages/academic conventions apply to the publication, while jurisdiction-specific source names and preferred authorities still require review."
        )
    else:
        profile["mode_note"] = profile["style_priority"]
    return profile
