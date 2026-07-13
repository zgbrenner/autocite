from autocite_mcp.cli import build_parser


def test_cli_exposes_deep_review_and_export_commands():
    parser = build_parser()
    review = parser.parse_args(["review", "text", "--deep-review", "--include-source-text"])
    assert review.command == "review"
    assert review.deep_review is True
    assert review.include_source_text is True

    exported = parser.parse_args(
        ["export-docx", "--original", "Id", "--corrected", "Id.", "--output", "review.docx"]
    )
    assert exported.command == "export-docx"
    assert exported.tracked is True

    jurisdictions = parser.parse_args(["jurisdictions"])
    assert jurisdictions.command == "jurisdictions"

    evaluation = parser.parse_args(["eval", "--file", "evals/gold.jsonl"])
    assert evaluation.command == "eval"
