"""Guardrail tests for the hardening of attacker-reachable surfaces."""

from __future__ import annotations

import base64
import io
import zipfile

import pytest

from autocite_mcp.documents import MAX_DOCUMENT_BYTES, DocumentLoadError, load_document_bytes
from autocite_mcp.document_ir import parse_docx_ir
from autocite_mcp.proposal_models import enforce_model_source_policy
from autocite_mcp.sources import _validated_courtlistener_url
from autocite_mcp.tools import review_uploaded_document


def test_model_policy_allows_defaults():
    enforce_model_source_policy(
        model_path="foolish-bandit/AutoCite-0.8B",
        base_model_id="Qwen/Qwen3.5-0.8B",
        offline_only=True,
    )


def test_model_policy_rejects_arbitrary_repositories(monkeypatch):
    monkeypatch.delenv("AUTOCITE_ALLOW_CUSTOM_MODELS", raising=False)
    with pytest.raises(ValueError, match="base_model_id is restricted"):
        enforce_model_source_policy(base_model_id="attacker/malicious-model")
    with pytest.raises(ValueError, match="model_path is restricted"):
        enforce_model_source_policy(model_path="attacker/malicious-adapter")
    with pytest.raises(ValueError, match="model_offline_only"):
        enforce_model_source_policy(offline_only=False)


def test_model_policy_operator_opt_in(monkeypatch):
    monkeypatch.setenv("AUTOCITE_ALLOW_CUSTOM_MODELS", "1")
    enforce_model_source_policy(base_model_id="my-org/custom-base", offline_only=False)


def test_courtlistener_follow_up_urls_are_host_validated():
    assert _validated_courtlistener_url(
        "https://www.courtlistener.com/api/rest/v4/clusters/1/"
    )
    assert _validated_courtlistener_url("https://attacker.example/steal-token") is None
    assert _validated_courtlistener_url("http://www.courtlistener.com/downgrade") is None
    assert _validated_courtlistener_url("") is None


def _docx_bytes(document_xml: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    return stream.getvalue()


def test_docx_with_doctype_is_rejected():
    payload = _docx_bytes(
        '<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY a "b">]>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
    )
    with pytest.raises(DocumentLoadError) as excinfo:
        load_document_bytes(payload, "evil.docx")
    assert excinfo.value.code == "invalid_docx"
    with pytest.raises(ValueError, match="document type declaration"):
        parse_docx_ir(payload)


def test_malformed_pdf_returns_clean_error_code():
    with pytest.raises(DocumentLoadError) as excinfo:
        load_document_bytes(b"%PDF-1.7 not really a pdf", "broken.pdf")
    assert excinfo.value.code in {"invalid_pdf", "ocr_required"}


@pytest.mark.asyncio
async def test_oversized_base64_rejected_before_decoding():
    oversized_length = (MAX_DOCUMENT_BYTES * 4) // 3 + 100
    file = {"file_name": "big.txt", "data_base64": "A" * oversized_length}
    with pytest.raises(DocumentLoadError) as excinfo:
        await review_uploaded_document(file)
    assert excinfo.value.code == "document_too_large"


@pytest.mark.asyncio
async def test_valid_base64_within_limit_still_loads():
    file = {
        "file_name": "memo.txt",
        "data_base64": base64.b64encode("See 42 U.S.C. § 1983.".encode()).decode(),
    }
    result = await review_uploaded_document(file)
    assert result["input_document"]["filename"] == "memo.txt"
