# Permissioned real-document evaluation

AutoCite's synthetic corpus remains useful for deterministic regression testing, but production confidence requires documents that reflect actual legal drafting and Word structure. This directory contains the schema and instructions for evaluating locally mounted, permissioned documents without committing those documents to Git.

## Privacy model

- Source documents remain outside the repository.
- Manifest paths are relative to a caller-supplied document root.
- Paths that escape the root are rejected.
- Every row requires an explicit permission basis.
- Reports contain document IDs and metrics, not source text or absolute paths.
- Standard evaluation disables local models, CourtListener, deep review, and other network-assisted features.
- The evaluator hashes each source before and after review and fails the release gate if the file changes.

Do not use privileged, confidential, personally identifying, licensed, or client material unless the owner has expressly authorized the evaluation and the evaluation environment is appropriate for it.

## Manifest format

Create a local JSONL manifest. Each nonempty line is one JSON object:

```json
{
  "document_id": "federal-brief-001",
  "relative_path": "federal/brief-001.docx",
  "split": "holdout",
  "permission": {
    "basis": "Author granted written permission for local evaluation",
    "reviewed_by": "evaluation-owner"
  },
  "mode": "bluepages",
  "document_type": "brief",
  "jurisdiction": "federal",
  "expected": {
    "citations": [
      {
        "text": "42 U.S.C. § 1983",
        "start": 418,
        "end": 435,
        "source_type": "statute"
      }
    ],
    "issue_codes": ["PROPOSITION_PINCITE_REVIEW"],
    "safe_fixed_text": "The complete expected text after permitted mechanical fixes."
  }
}
```

`safe_fixed_text` is optional, but strongly recommended for release-gate documents because it detects unintended prose changes. Keep the manifest in the same protected location as the source documents when it contains document text.

Allowed splits are `train`, `dev`, `test`, and `holdout`. Release decisions should rely on `test` or `holdout` documents that were not used to design the relevant rule or fix.

## Run

After installing AutoCite from a checkout:

```bash
uv run autocite-eval-real \
  --manifest /secure/autocite-eval/manifest.jsonl \
  --documents-root /secure/autocite-eval/documents \
  --output outputs/real-document-evaluation.json
```

The command exits with status 0 only when every document passes all mandatory gates.

## Mandatory gates

A document fails when any of the following occurs:

- citation precision or recall is below 1.0 for declared gold citations;
- issue-code precision or recall is below 1.0;
- corrected text differs from `safe_fixed_text` when provided;
- an applied edit is not a high-confidence `safe_auto_fix`;
- an antecedent is guessed rather than resolved or explicitly left ambiguous;
- a local-mode network result appears;
- the source file changes;
- the preservation-first DOCX export cannot be produced and validated;
- review raises an exception.

## Recommended corpus composition

Include clean and malformed documents across:

- federal and state briefs and motions;
- legal memoranda;
- law-review and seminar-paper footnotes;
- tables, headers, footers, comments, tracked changes, hyperlinks, fields, and section breaks;
- short-form chains, multi-authority citation groups, `Id.`, `supra`, and `hereinafter`;
- statutes, regulations, constitutions, cases, journals, internet sources, and unsupported-source probes;
- searchable PDFs and deliberately image-only PDFs;
- documents that must produce no changes.

At least two legally trained reviewers should independently label high-stakes holdout documents and reconcile disagreements without consulting AutoCite's output.