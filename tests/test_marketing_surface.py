from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_first_screen_leads_with_product_value_and_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")[:3500].lower()
    assert "private legal citation checker" in readme
    assert "local-first" in readme
    assert "github.com/zgbrenner/autocite/releases/latest" in readme
    assert "citation risk scan" in readme
    assert "does not guarantee complete bluebook compliance" in readme


def test_site_contains_the_complete_search_and_growth_surface():
    required = [
        "site/src/pages/index.astro",
        "site/src/pages/citation-risk-scan/index.astro",
        "site/src/pages/compare/generic-ai.astro",
        "site/src/pages/download/index.astro",
        "site/src/pages/guides/index.astro",
        "site/public/robots.txt",
        "site/public/llms.txt",
        "site/scripts/audit-seo.mjs",
        "docs/marketing/POSITIONING.md",
        "docs/marketing/LAUNCH-KIT.md",
        "docs/marketing/CONTENT-CALENDAR.md",
    ]
    for relative in required:
        assert (ROOT / relative).is_file(), relative

    guides = list((ROOT / "site/src/content/guides").glob("*.md"))
    assert len(guides) >= 6


def test_site_has_no_analytics_dependency_or_inflated_claim_language():
    package = (ROOT / "site/package.json").read_text(encoding="utf-8").lower()
    for analytics_package in ("google-analytics", "@vercel/analytics", "posthog", "plausible"):
        assert analytics_package not in package

    public_copy = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "site/src").rglob("*")
        if path.is_file() and path.suffix in {".astro", ".ts", ".md"}
    ).lower()
    for prohibited in (
        "100% accurate",
        "guaranteed accuracy",
        "one-click bluebook compliance",
        "never make a citation mistake again",
        "replaces legal judgment",
    ):
        assert prohibited not in public_copy


def test_site_ci_enforces_locked_build_browser_privacy_and_lighthouse():
    workflow = (ROOT / ".github/workflows/site-ci.yml").read_text(encoding="utf-8")
    for required in (
        "node-version: 22",
        "npm ci",
        "npm run lint",
        "npm test",
        "npm run build",
        "npm run audit:seo",
        "npm run test:e2e",
        "npm run lighthouse:ci",
        "Site quality gate",
    ):
        assert required in workflow
