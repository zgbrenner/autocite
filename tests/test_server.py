from __future__ import annotations

from autocite_mcp.server import mcp


async def test_mcp_exposes_expected_tools_resources_and_prompts() -> None:
    tools = await mcp.list_tools()
    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()
    prompts = await mcp.list_prompts()

    assert {tool.name for tool in tools} == {
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
        "autocite://capabilities"
    }
    assert {str(template.uriTemplate) for template in templates} == {
        "autocite://rules/{mode}"
    }
    assert {prompt.name for prompt in prompts} == {
        "court_filing_citecheck",
        "law_review_citecheck",
        "citation_repair",
    }
