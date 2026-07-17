"""Opt-in real-model smoke test for the published AutoCite adapter.

This script is intentionally excluded from ordinary CI. Run it only after installing the
``slm`` extra and predownloading the model, or pass ``--allow-download`` explicitly.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from autocite_mcp.proposal_models import LocalQwenProposalModel, ModelRuntimeConfig
from autocite_mcp.slm import CitationProposal, validate_proposal
from autocite_mcp.slm_runtime import CitationTask, render_prompt


async def _generate(model: LocalQwenProposalModel, task: CitationTask) -> CitationProposal:
    raw = await model.generate(render_prompt(task))
    json.loads(raw)
    return CitationProposal.from_json(raw)


def _task(text: str, source_type: str, issue_code: str) -> CitationTask:
    return CitationTask(
        citation_text=text,
        citation_start=4,
        citation_end=4 + len(text),
        source_type=source_type,
        mode="bluepages",
        context=f"See {text}.",
        context_start=0,
        deterministic_issues=({"code": issue_code},),
        components={},
    )


async def smoke(*, allow_download: bool = False) -> dict[str, bool]:
    model = LocalQwenProposalModel(
        ModelRuntimeConfig(enabled=True, offline_only=not allow_download)
    )
    statute = await _generate(
        model, _task("42 USC §1983", "statute", "STATUTE_CODE_ABBREVIATION")
    )
    regulation = await _generate(
        model,
        _task("17 CFR §240.10b-5", "regulation", "REGULATION_CODE_ABBREVIATION"),
    )
    incomplete_case = await _generate(
        model, _task("Smith v. Jones", "case", "INSUFFICIENT_INFORMATION")
    )
    unsupported = CitationProposal.from_mapping(
        {
            "citation_text": "42 USC §1983",
            "start": 0,
            "end": 12,
            "source_type": "statute",
            "mode": "bluepages",
            "issue_code": "STATUTE_CODE_ABBREVIATION",
            "proposed_citation": "42 U.S.C. § 1983 (2024)",
            "facts_used": {"title": "42", "section": "1983"},
            "missing_facts": [],
            "antecedent_candidate": None,
            "confidence": "high",
            "abstain": False,
            "explanation": "Proposed normalization.",
            "retrieved_rule_chunk_ids": [],
        }
    )
    unsupported_result = validate_proposal(
        unsupported,
        "42 USC §1983",
        expected_mode="bluepages",
        expected_source_type="statute",
    )
    results = {
        "statute_normalization": statute.proposed_citation == "42 U.S.C. § 1983",
        "regulation_normalization": regulation.proposed_citation
        == "17 C.F.R. § 240.10b-5",
        "incomplete_case_abstention": incomplete_case.abstain
        and incomplete_case.proposed_citation is None,
        "valid_structured_json": True,
        "unsupported_fact_rejected": "unsupported_material_facts"
        in unsupported_result.reasons,
    }
    if not all(results.values()):
        raise RuntimeError(f"adapter smoke test failed: {results}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(smoke(allow_download=args.allow_download)), indent=2))


if __name__ == "__main__":
    main()
