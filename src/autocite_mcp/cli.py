from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Any

from .evals import run_gold_evaluation
from .formatters import generate_citation
from .setup_clients import install_claude_desktop
from .slm_runtime import DEFAULT_MODEL
from .tools import (
    check_citations,
    export_review_docx,
    get_citation_guidance,
    list_capabilities,
    list_jurisdiction_profiles,
    review_document,
    review_uploaded_document,
)


def _read_text(value: str | None, file_path: str | None) -> str:
    if value is not None:
        return value
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    return sys.stdin.read()


def _emit(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _add_review_options(command: argparse.ArgumentParser) -> None:
    command.add_argument("--document-type", default="auto")
    command.add_argument("--mode", choices=("auto", "bluepages", "whitepages"), default="auto")
    command.add_argument("--jurisdiction")
    command.add_argument("--no-fix", action="store_true")
    command.add_argument("--verify-cases", action="store_true")
    command.add_argument("--deep-review", action="store_true")
    command.add_argument("--include-source-text", action="store_true")
    command.add_argument("--slm", action="store_true", help="Enable optional local SLM review")
    command.add_argument("--model-path", default=DEFAULT_MODEL)
    command.add_argument("--slm-only", action="store_true", help="Skip deterministic edits for evaluation")
    command.add_argument("--apply-slm-fixes", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autocite",
        description="Audit, evidence-check, fix, and export legal citations without an MCP client.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    review = subparsers.add_parser("review", help="Run the complete automatic citecheck workflow")
    review.add_argument("text", nargs="?")
    review.add_argument("--file")
    _add_review_options(review)

    review_file = subparsers.add_parser(
        "review-file", help="Review TXT, Markdown, DOCX, or text-based PDF"
    )
    review_file.add_argument("file", type=Path)
    _add_review_options(review_file)

    for name in ("check", "fix"):
        command = subparsers.add_parser(name)
        command.add_argument("text", nargs="?")
        command.add_argument("--file")
        command.add_argument(
            "--mode", choices=("bluepages", "whitepages"), default="bluepages"
        )

    generate = subparsers.add_parser("generate")
    generate.add_argument("source_type")
    generate.add_argument("--fields", required=True, help="JSON object of source facts")
    generate.add_argument(
        "--mode", choices=("bluepages", "whitepages"), default="bluepages"
    )
    generate.add_argument(
        "--output-style", choices=("plain", "markdown", "html"), default="plain"
    )

    guidance = subparsers.add_parser("guidance")
    guidance.add_argument("--mode", choices=("bluepages", "whitepages"), default="bluepages")
    guidance.add_argument("--source-type", default="all")

    export = subparsers.add_parser("export-docx", help="Create a corrected DOCX review artifact")
    export.add_argument("--original")
    export.add_argument("--original-file")
    export.add_argument("--corrected")
    export.add_argument("--corrected-file")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--no-track", dest="tracked", action="store_false", default=True)

    setup = subparsers.add_parser("setup-claude", help="Install AutoCite into Claude Desktop")
    setup.add_argument("--config", type=Path)
    setup.add_argument("--courtlistener-token")

    evaluation = subparsers.add_parser("eval", help="Run deterministic AutoCite gold fixtures")
    evaluation.add_argument("--file", type=Path, default=Path("evals/gold.jsonl"))

    subparsers.add_parser("jurisdictions", help="List federal and state profiles")
    subparsers.add_parser("capabilities")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "review":
        text = _read_text(args.text, args.file)
        _emit(
            asyncio.run(
                review_document(
                    text,
                    document_type=args.document_type,
                    mode=args.mode,
                    jurisdiction=args.jurisdiction,
                    apply_safe_fixes=not args.no_fix,
                    verify_cases=args.verify_cases,
                    deep_review=args.deep_review,
                    include_source_text=args.include_source_text,
                    use_slm=args.slm or args.slm_only,
                    model_path=args.model_path,
                    slm_only=args.slm_only,
                    apply_slm_fixes=args.apply_slm_fixes,
                )
            )
        )
        return
    if args.command == "review-file":
        path: Path = args.file
        payload = {
            "file_name": path.name,
            "data_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
        _emit(
            asyncio.run(
                review_uploaded_document(
                    payload,
                    document_type=args.document_type,
                    mode=args.mode,
                    jurisdiction=args.jurisdiction,
                    apply_safe_fixes=not args.no_fix,
                    deep_review=args.deep_review,
                    include_source_text=args.include_source_text,
                    use_slm=args.slm or args.slm_only,
                    model_path=args.model_path,
                    slm_only=args.slm_only,
                    apply_slm_fixes=args.apply_slm_fixes,
                )
            )
        )
        return
    if args.command in {"check", "fix"}:
        text = _read_text(args.text, args.file)
        _emit(
            check_citations(
                text,
                mode=args.mode,
                apply_safe_fixes=args.command == "fix",
            )
        )
        return
    if args.command == "generate":
        fields = json.loads(args.fields)
        if not isinstance(fields, dict):
            raise ValueError("--fields must decode to a JSON object")
        _emit(
            {
                "citation": generate_citation(
                    args.source_type,
                    fields,
                    mode=args.mode,
                    output_style=args.output_style,
                )
            }
        )
        return
    if args.command == "guidance":
        _emit(get_citation_guidance(mode=args.mode, source_type=args.source_type))
        return
    if args.command == "export-docx":
        original = _read_text(args.original, args.original_file)
        corrected = _read_text(args.corrected, args.corrected_file)
        artifact = export_review_docx(
            original,
            corrected,
            tracked=args.tracked,
            filename=args.output.name,
        )
        args.output.write_bytes(base64.b64decode(artifact["data_base64"]))
        _emit({key: value for key, value in artifact.items() if key != "data_base64"} | {"output": str(args.output)})
        return
    if args.command == "setup-claude":
        _emit(
            install_claude_desktop(
                config_path=args.config,
                courtlistener_token=args.courtlistener_token,
            )
        )
        return
    if args.command == "eval":
        _emit(run_gold_evaluation(args.file))
        return
    if args.command == "jurisdictions":
        _emit(list_jurisdiction_profiles())
        return
    _emit(list_capabilities())


if __name__ == "__main__":
    main()
