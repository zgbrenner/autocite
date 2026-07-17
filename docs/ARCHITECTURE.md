# Architecture

AutoCite is one local Python core with five interfaces: direct API, CLI, stdio MCP, loopback MCP, and PySide desktop. `DocumentIR` preserves structure; extractors identify citations; the citation graph owns authority identity and antecedents; declared deterministic rules emit correction levels; approved local Markdown supplies attributed context; optional Qwen proposes structured output; the validator alone decides eligibility; exporters write only caller-selected artifacts.

Automatic edits flow only from deterministic `safe_auto_fix` findings. Models, retrieval, rerankers, and external verification cannot modify documents. CourtListener is an explicit external evidence source and never a citator.
