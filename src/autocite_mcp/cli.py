from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .formatters import generate_citation
from .setup_clients import install_claude_desktop
from .tools import (
    check_citations,
    get_citation_guidance,
    list_capabilities,
    review_document,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autocite",
        description="Audit, fix, and generate legal citations without an MCP client.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    review = subparsers.add_parser("review", help="Run the complete automatic citecheck workflow")
    review.add_argument("text", nargs="?")
    review.add_argument("--file")
    review.add_argument("--document-type", default="auto")
    review.add_argument("--mode", choices=("auto", "bluepages", "whitepages"), default="auto")
    review.add_argument("--jurisdiction")
    review.add_argument("--no-fix", action="store_true")
    review.add_argument("--verify-cases", action="store_true")

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

    setup = subparsers.add_parser("setup-claude", help="Install AutoCite into Claude Desktop")
    setup.add_argument("--config", type=Path)
    setup.add_argument("--courtlistener-token")

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
    if args.command == "setup-claude":
        _emit(
            install_claude_desktop(
                config_path=args.config,
                courtlistener_token=args.courtlistener_token,
            )
        )
        return
    _emit(list_capabilities())


if __name__ == "__main__":
    main()
