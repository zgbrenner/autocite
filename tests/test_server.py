from __future__ import annotations

from autocite_mcp.server import mcp


async def test_mcp_exposes_expected_tools_resources_and_prompts() -> None:
    tools = await mcp.list_tools()
    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()
    prompts = await mcp.list_prompts()

    assert {tool.name for tool in tools} == {
        "review_document",
        "get_citation_guidance",
        "check_citations",
        "fix_citations",
        "check_single_citation",
        "convert_citation",
        "generate_citation",
        "verify_case_citations",
        "explain_issue",
        "list_capabilities",
    }
    assert {str(resource.uri) for resource in resources} == {
        "autocite://capabilities",
        "autocite://knowledge/core",
    }
    assert {str(template.uriTemplate) for template in templates} == {
        "autocite://rules/{mode}",
        "autocite://knowledge/{mode}/{source_type}",
    }
    assert {prompt.name for prompt in prompts} == {
        "complete_citecheck",
        "court_filing_citecheck",
        "law_review_citecheck",
        "citation_repair",
    }


async def test_http_health_route_is_available() -> None:
    import json

    from autocite_mcp.server import health_check

    assert "/health" in {route.path for route in mcp.streamable_http_app().routes}
    response = await health_check(None)  # type: ignore[arg-type]
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["service"] == "autocite-mcp"
    assert payload["mcp_endpoint"] == "/mcp"
