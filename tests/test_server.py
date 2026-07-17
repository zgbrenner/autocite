from __future__ import annotations

from autocite_mcp.server import mcp


def test_review_tools_expose_optional_slm_parameters() -> None:
    import inspect

    from autocite_mcp.server import review_document, review_uploaded_document

    review_parameters = inspect.signature(review_document).parameters
    upload_parameters = inspect.signature(review_uploaded_document).parameters
    for name in (
        "use_slm",
        "use_local_model",
        "model_path",
        "base_model_id",
        "local_model_directory",
        "model_device",
        "model_quantization",
        "model_offline_only",
        "model_max_context_length",
        "model_max_generated_tokens",
        "model_timeout_seconds",
        "model_seed",
        "slm_only",
        "apply_slm_fixes",
    ):
        assert name in review_parameters
        assert name in upload_parameters


async def test_mcp_exposes_expected_tools_resources_and_prompts() -> None:
    tools = await mcp.list_tools()
    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()
    prompts = await mcp.list_prompts()

    assert {tool.name for tool in tools} == {
        "review_document",
        "review_uploaded_document",
        "export_review_docx",
        "open_citecheck_workspace",
        "get_jurisdiction_profile",
        "list_jurisdiction_profiles",
        "get_citation_guidance",
        "check_citations",
        "get_citation_graph",
        "resolve_short_form",
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
        "ui://autocite/citecheck-v1.html",
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

    uploaded = next(tool for tool in tools if tool.name == "review_uploaded_document")
    assert uploaded.meta["openai/fileParams"] == ["file"]
    workspace = next(tool for tool in tools if tool.name == "open_citecheck_workspace")
    assert workspace.meta["ui"]["resourceUri"] == "ui://autocite/citecheck-v1.html"


async def test_http_health_route_is_available() -> None:
    import json

    from autocite_mcp.server import health_check

    assert "/health" in {route.path for route in mcp.streamable_http_app().routes}
    response = await health_check(None)  # type: ignore[arg-type]
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert payload["service"] == "autocite-mcp"
    assert payload["mcp_endpoint"] == "/mcp"
