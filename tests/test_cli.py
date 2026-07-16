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


def test_cli_exposes_optional_slm_review_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "review",
            "See 42 USC §1983.",
            "--slm",
            "--model-path",
            "local/autocite",
            "--apply-slm-fixes",
        ]
    )
    assert args.slm is True
    assert args.model_path == "local/autocite"
    assert args.apply_slm_fixes is True
    assert args.slm_only is False

    only = parser.parse_args(["review", "Id. at 4.", "--slm-only"])
    assert only.slm_only is True
