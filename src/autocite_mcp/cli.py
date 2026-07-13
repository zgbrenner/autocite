from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .formatters import generate_citation
from .tools import check_citations, list_capabilities


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
        description="Audit and generate legal citations without an MCP client.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    subparsers.add_parser("capabilities")
    return parser


def main() -> None:
    args = build_parser().parse_args()
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
    _emit(list_capabilities())


if __name__ == "__main__":
    main()
