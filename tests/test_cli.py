import os
import subprocess
import sys

from autocite_mcp.cli import build_parser


def test_cli_emits_utf8_citation_symbols_regardless_of_console_codepage():
    # pytest's own stdout capture always presents a UTF-8-safe stream, which
    # masks a real regression: a non-UTF-8 platform console/locale (e.g. the
    # legacy Windows ANSI codepage) makes plain `sys.stdout.write()` emit
    # legacy-codepage bytes for non-ASCII citation symbols like `§`/`¶`,
    # which any UTF-8-expecting consumer downstream then corrupts. Spawn the
    # real CLI as a subprocess with a forced non-UTF-8 PYTHONIOENCODING to
    # reproduce that condition and assert stdout is still valid UTF-8.
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    result = subprocess.run(
        [sys.executable, "-m", "autocite_mcp.cli", "check", "See 42 U.S.C. § 1983; id. ¶ 12."],
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    stdout_text = result.stdout.decode("utf-8")  # raises UnicodeDecodeError on mangled/legacy-codepage bytes
    assert "§" in stdout_text
    assert "¶" in stdout_text


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
