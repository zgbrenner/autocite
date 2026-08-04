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
        "generate_certification_report",
        "open_citecheck_workspace",
        "get_jurisdiction_profile",
        "list_jurisdiction_profiles",
        "get_citation_guidance",
        "check_citations",
        "get_citation_graph",
        "resolve_short_form",
        "get_rule_coverage",
        "get_rule_context",
        "fix_citations",
        "check_single_citation",
        "convert_citation",
        "generate_citation",
        "verify_case_citations",
        "explain_issue",
        "list_capabilities",
        "health_check",
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

    from autocite_mcp.server import health_route

    assert "/health" in {route.path for route in mcp.streamable_http_app().routes}
    response = await health_route(None)  # type: ignore[arg-type]
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert payload["service"] == "autocite-mcp"
    assert payload["mcp_endpoint"] == "/mcp"


SAMPLE_TEXT = (
    "See Brown v. Board of Education, 347 U.S. 483 (1954). Id. at 495. "
    "See also 42 U.S.C. § 1983."
)


async def test_every_tool_declares_a_real_output_schema() -> None:
    """Every tool must advertise an outputSchema with actual field information.

    Before typed output models, every tool's return annotation was
    ``dict[str, Any]`` (or ``list[dict]``), which FastMCP still turns into an
    ``outputSchema``, but a useless one: ``{"type": "object",
    "additionalProperties": true}`` with no declared properties. This test
    guards against silently regressing back to that state.
    """
    tools = await mcp.list_tools()
    assert tools, "expected at least one registered tool"
    for tool in tools:
        schema = tool.outputSchema
        assert schema is not None, f"{tool.name} has no outputSchema"
        additional_properties = schema.get("additionalProperties")
        has_declared_shape = (
            bool(schema.get("properties"))
            or "$ref" in schema
            or bool(schema.get("items"))
            or isinstance(additional_properties, dict)
        )
        assert has_declared_shape, (
            f"{tool.name} outputSchema has no declared properties: {schema!r}"
        )


async def test_representative_tool_calls_produce_valid_structured_content() -> None:
    """A real invocation of most tools must yield structuredContent that matches its schema.

    ``FuncMetadata.convert_result`` (mcp.server.fastmcp.utilities.func_metadata)
    calls ``output_model.model_validate(result)`` before building
    ``structuredContent``; if a tool's payload didn't actually match its
    declared output model this call would raise, so simply getting
    structured content back here is itself the validation.
    """
    calls: dict[str, dict[str, object]] = {
        "health_check": {},
        "review_document": {"text": SAMPLE_TEXT},
        "export_review_docx": {"original_text": "a", "corrected_text": "b"},
        "generate_certification_report": {"text": SAMPLE_TEXT, "prepared_for": "Test Court"},
        "open_citecheck_workspace": {"text": SAMPLE_TEXT},
        "get_jurisdiction_profile": {"identifier": "federal"},
        "list_jurisdiction_profiles": {},
        "get_citation_guidance": {},
        "check_citations": {"text": SAMPLE_TEXT},
        "get_citation_graph": {"text": SAMPLE_TEXT},
        "resolve_short_form": {"text": SAMPLE_TEXT},
        "get_rule_coverage": {},
        "get_rule_context": {"query": "pincite"},
        "fix_citations": {"text": SAMPLE_TEXT},
        "check_single_citation": {"citation": "347 U.S. 483 (1954)"},
        "convert_citation": {
            "citation": "Brown v. Board of Education, 347 U.S. 483 (1954)",
            "target_mode": "bluepages",
        },
        "generate_citation": {
            "source_type": "case",
            "fields": {
                "case_name": "Brown v. Board",
                "volume": "347",
                "reporter": "U.S.",
                "first_page": "483",
                "year": "1954",
            },
        },
        "verify_case_citations": {"text": SAMPLE_TEXT},
        "explain_issue": {"code": "CASE_PINCITE_REVIEW"},
        "list_capabilities": {},
    }
    tool_names = {tool.name for tool in await mcp.list_tools()}
    assert set(calls) | {"review_uploaded_document"} == tool_names

    for name, arguments in calls.items():
        content, structured = await mcp.call_tool(name, arguments)
        assert content, f"{name} returned no unstructured content"
        assert structured, f"{name} returned no structuredContent"


async def test_review_uploaded_document_structured_content_validates() -> None:
    import base64

    file_payload = {
        "file_name": "doc.txt",
        "mime_type": "text/plain",
        "data_base64": base64.b64encode(SAMPLE_TEXT.encode("utf-8")).decode("ascii"),
    }
    content, structured = await mcp.call_tool(
        "review_uploaded_document", {"file": file_payload}
    )
    assert content
    assert structured["input_document"]["filename"] == "doc.txt"
    assert structured["input_document"]["sha256"]
    assert structured["corrected_text"]


async def test_review_document_structured_content_deep_shape() -> None:
    """Deep-shape check: nested citation graph, mode detection, and citations validate."""
    content, structured = await mcp.call_tool("review_document", {"text": SAMPLE_TEXT})
    assert content

    assert structured["schema_version"] == "1.0"
    assert structured["mode"] == "bluepages"

    mode_detection = structured["mode_detection"]
    assert mode_detection["mode"] == "bluepages"
    assert isinstance(mode_detection["evidence"], list)

    profile = structured["jurisdiction_profile"]
    assert profile["id"] == "federal"
    assert profile["selected_mode"] == "bluepages"

    citations = structured["citation_inventory"]
    assert citations, "expected at least one detected citation"
    first = citations[0]
    assert {"source_type", "text", "start", "end", "components"} <= first.keys()

    graph = structured["citation_graph"]
    assert graph["mode"] == "bluepages"
    assert graph["authorities"], "expected at least one authority node"
    authority = graph["authorities"][0]
    assert {"authority_id", "source_type", "identity_key", "display_name", "components"} <= (
        authority.keys()
    )
    assert graph["occurrences"], "expected at least one occurrence node"
    occurrence = graph["occurrences"][0]
    assert "location" in occurrence
    assert {"absolute_start", "absolute_end"} <= occurrence["location"].keys()
    assert graph["edges"]
    assert graph["resolutions"], "Id. should resolve against the preceding case"
    resolution = graph["resolutions"][0]
    assert resolution["resolved_authority_id"]
    assert resolution["candidates"]

    knowledge = structured["knowledge"]
    assert knowledge["jurisdiction_profile"]["id"] == "federal"
    assert "case" in knowledge["sources"]

    verification = structured["case_verification"]
    assert verification["available"] is False

    retrieval = structured["retrieval"]
    assert isinstance(retrieval["triggered"], bool)
    assert isinstance(retrieval["chunks"], list)


async def test_generate_certification_report_structured_content_deep_shape() -> None:
    content, structured = await mcp.call_tool(
        "generate_certification_report",
        {"text": SAMPLE_TEXT, "prepared_for": "Test Court"},
    )
    assert content

    assert structured["schema_version"] == "1.0"
    assert structured["report_type"] == "citation_review_audit"
    assert structured["prepared_for"] == "Test Court"
    assert structured["citation_count"] == len(structured["citations"])

    tier_counts = structured["verification_tier_counts"]
    assert set(tier_counts) == {
        "mechanical_only",
        "source_matched",
        "source_not_matched",
        "evidence_prepared",
    }
    assert sum(tier_counts.values()) == structured["citation_count"]

    for entry in structured["citations"]:
        assert {"citation", "source_type", "span", "verification_tier"} <= entry.keys()
        assert len(entry["span"]) == 2

    assert "## Citations" in structured["markdown"]
    assert structured["statement"]


async def test_check_citations_does_not_block_the_event_loop_on_a_dense_document() -> None:
    # check_citations previously ran directly on the event loop (a plain
    # `def` tool, called synchronously by FastMCP's dispatch), so a
    # citation-dense document would stall every other concurrent request
    # against a hosted server for the full duration of the call -- the same
    # class of issue fixed for review_document via
    # tools._run_deterministic_pipeline, but left open here. Now offloaded
    # via asyncio.to_thread; a concurrent heartbeat task must keep ticking
    # throughout the call.
    import asyncio

    from autocite_mcp.server import check_citations

    dense_text = "Brown v. Board of Education, 347 U.S. 483 (1954). " * 500
    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0)
            ticks += 1

    hb = asyncio.create_task(heartbeat())
    await check_citations(dense_text)
    hb.cancel()
    assert ticks > 5


def test_generate_citation_echoes_normalized_mode_and_style():
    from autocite_mcp.server import generate_citation

    out = generate_citation(
        "statute",
        {"title": "42", "code": "USC", "section": "1983"},
        mode=" BLUEPAGES ",
        output_style=" PLAIN ",
    )
    assert out["mode"] == "bluepages"
    assert out["output_style"] == "plain"
    assert out["citation"] == "42 U.S.C. § 1983"
