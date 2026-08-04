import type { AudiencePageData } from "../components/AudiencePage.astro";

export const audiencePages: AudiencePageData[] = [
  {
    slug: "bluebook-citation-checker",
    title: "Bluebook citation checker for private document review",
    h1: "A Bluebook citation checker built around the document, not a chatbot.",
    description:
      "Review supported Bluepages and Whitepages citation mechanics locally with exact spans, transparent limits, and no application telemetry.",
    lead:
      "AutoCite reviews legal citations inside briefs, motions, memoranda, seminar papers, and journal drafts while preserving the surrounding prose. It separates supported mechanical fixes from questions that still require legal or editorial judgment.",
    asideTitle: "Bluepages and Whitepages",
    asideBody:
      "AutoCite can select a practitioner or academic workflow automatically, and the reviewer can override the mode when the document needs a different treatment.",
    sections: [
      {
        title: "What a responsible Bluebook checker should do",
        paragraphs: [
          "A citation checker should identify the exact text it is evaluating, explain the rule family, and avoid filling missing fields with plausible-looking facts. AutoCite treats the citation as structured evidence rather than an invitation to rewrite the paragraph.",
          "Only supported, high-confidence mechanical corrections are eligible for automatic application. Ambiguous short forms, source relationships, quotations, and pinpoint questions remain visible for review.",
        ],
        bullets: [
          "Normalize supported federal reporter and code abbreviations.",
          "Check section-symbol spacing and narrow short-form mechanics.",
          "Preserve original document text and maintain a separate working revision.",
          "Show unresolved issues without pretending they are complete legal conclusions.",
        ],
      },
      {
        title: "What AutoCite intentionally does not promise",
        paragraphs: [
          "AutoCite does not claim complete Bluebook compliance. It does not determine that an authority is good law, controlling, persuasive, or supportive of a proposition. Optional source retrieval can surface candidate passages, but legal judgment remains with the reviewer.",
        ],
      },
      {
        title: "Use it with Word documents and searchable PDFs",
        paragraphs: [
          "The desktop workflow accepts DOCX, searchable PDF, Markdown, and TXT. The application can export reviewed copies and preserve a clear record of accepted and rejected citation issues. Image-only PDFs need OCR before reliable text review.",
        ],
      },
    ],
    faq: [
      {
        question: "Is AutoCite an official Bluebook product?",
        answer:
          "No. AutoCite is independent, open-source software and is not affiliated with or endorsed by the publishers or editors of The Bluebook.",
      },
      {
        question: "Can it review both Bluepages and Whitepages citations?",
        answer:
          "Yes, within published supported coverage. AutoCite distinguishes practitioner and academic workflows and exposes the selected mode to the reviewer.",
      },
      {
        question: "Will it rewrite my legal analysis?",
        answer:
          "AutoCite is designed to preserve non-citation prose. Automatic changes are limited to supported citation mechanics with exact source spans.",
      },
    ],
  },
  {
    slug: "legal-citation-checker",
    title: "Legal citation checker for briefs, motions, and articles",
    h1: "Check legal citations without handing the document to a general-purpose AI.",
    description:
      "AutoCite is a local-first legal citation checker for briefs, motions, memoranda, law-review drafts, and academic legal writing.",
    lead:
      "Legal citation review is not ordinary proofreading. AutoCite keeps citation extraction, deterministic corrections, document structure, and reviewer decisions in a purpose-built workflow.",
    asideTitle: "Privacy by default",
    asideBody:
      "Standard desktop review stays local. Network-backed source review is optional and explicitly labeled before citation text is sent to CourtListener.",
    sections: [
      {
        title: "Citation review needs narrower authority than prose generation",
        paragraphs: [
          "A fluent model can make an invented reporter, year, page, or parenthetical look credible. AutoCite therefore refuses to generate missing citation facts during automatic correction and validates every eligible edit against the original span.",
        ],
      },
      {
        title: "Document-wide relationships matter",
        paragraphs: [
          "Short forms such as Id., supra, and shortened case names depend on what appeared earlier and where it appeared. AutoCite builds a conservative document citation graph so ambiguous relationships can be surfaced instead of guessed.",
        ],
        bullets: [
          "Authority identities and every occurrence remain inspectable.",
          "Ambiguous antecedents return bounded candidates and a review warning.",
          "Footnote, page, and document-block locations remain attached where available.",
        ],
      },
      {
        title: "A reviewer remains accountable",
        paragraphs: [
          "AutoCite can reduce mechanical work and create a better audit trail, but it does not replace source verification, a licensed citator, controlling local rules, journal-specific requirements, or professional judgment.",
        ],
      },
    ],
    faq: [
      {
        question: "Can AutoCite verify case quotations?",
        answer:
          "Optional deep review can retrieve matched CourtListener opinion text and compare nearby quotations or page markers. It does not conclude that a source supports the legal proposition or remains good law.",
      },
      {
        question: "Does AutoCite work offline?",
        answer:
          "Standard deterministic desktop review is local-first and does not require source-retrieval network calls. Optional model and CourtListener features have separate setup and privacy disclosures.",
      },
      {
        question: "Which jurisdictions are supported?",
        answer:
          "AutoCite includes curated federal and California priority profiles plus safe generic profiles for all fifty states. Generic state profiles explicitly require current local-rule review.",
      },
    ],
  },
  {
    slug: "law-students",
    title: "Bluebook citation checker for law students",
    h1: "Spend less time hunting mechanical citation mistakes before the deadline.",
    description:
      "A private Bluebook citation checker for legal-writing assignments, seminar papers, journal write-ons, and student notes.",
    lead:
      "AutoCite gives law students a structured second pass for supported citation mechanics without rewriting the argument or turning missing citation facts into confident guesses.",
    asideTitle: "Learn from every issue",
    asideBody:
      "Each finding includes the original span, issue family, proposed change, explanation, confidence, and correction level.",
    sections: [
      {
        title: "Use AutoCite after your substantive edit",
        paragraphs: [
          "Finish the legal analysis first. Then open the document in AutoCite, confirm whether the work follows a Bluepages or Whitepages workflow, and review each citation issue alongside the original text.",
        ],
        bullets: [
          "Memos, briefs, motions, and practical assignments usually use Bluepages priorities.",
          "Seminar papers, student notes, and journal work usually use Whitepages priorities.",
          "Your professor, journal, or court may impose requirements beyond AutoCite's supported checks.",
        ],
      },
      {
        title: "Do not outsource the source check",
        paragraphs: [
          "The tool can help expose mechanical risk, but students still need to open authorities, confirm quotations and pincites, evaluate support, and follow the exact assignment instructions. AutoCite's visible limitations are part of the learning workflow.",
        ],
      },
      {
        title: "Private enough for drafts",
        paragraphs: [
          "Standard desktop review stays on the user's computer and the application has no telemetry. That is useful for unpublished student work, clinic drafts, and journal materials that should not be pasted into a public chatbot.",
        ],
      },
    ],
    faq: [
      {
        question: "Can I use AutoCite for a law-school memo?",
        answer:
          "Yes. Use the practitioner-oriented Bluepages workflow, then follow the professor's assignment instructions and any local citation rules that go beyond supported coverage.",
      },
      {
        question: "Does AutoCite write citations from scratch?",
        answer:
          "It can format or generate citations from facts the user supplies, but it refuses required missing facts rather than inventing them.",
      },
      {
        question: "Can my journal use it for a write-on competition?",
        answer:
          "That depends on the competition rules. Participants should obtain permission before using any automated citation tool.",
      },
    ],
    ctaHeading: "Give your next citation pass a real workflow.",
  },
  {
    slug: "law-review",
    title: "Law review and journal citation checker",
    h1: "A citation-review workspace for long drafts, footnotes, and short forms.",
    description:
      "Review law-review articles, student notes, and journal drafts with Whitepages priorities, document-wide citation relationships, and transparent issue decisions.",
    lead:
      "Journal citation work is relational. AutoCite keeps footnotes, source locations, authority occurrences, and short-form candidates visible so editors can make decisions without losing the document's structure.",
    asideTitle: "Editorial control stays visible",
    asideBody:
      "Editors can accept or reject issues individually, compare revisions, and export reviewed copies while retaining unresolved questions.",
    sections: [
      {
        title: "Whitepages review without black-box rewriting",
        paragraphs: [
          "AutoCite can identify supported citation families and mechanical inconsistencies while preserving the author's prose. It does not flatten a footnoted article into a summary or silently replace uncertain citations.",
        ],
      },
      {
        title: "Short forms need document context",
        paragraphs: [
          "The citation graph records authority identities and occurrences across the document. Id., supra, supra note, hereinafter, and shortened-case questions can therefore return explicit resolutions or bounded candidates instead of unsupported guesses.",
        ],
        bullets: [
          "DOCX footnotes and endnotes remain distinct from body text where parsing supports them.",
          "Markdown note identifiers and searchable PDF page evidence remain attached.",
          "Ambiguous relationships remain review-required.",
        ],
      },
      {
        title: "Journal-specific rules still control",
        paragraphs: [
          "AutoCite's published rule coverage cannot substitute for a journal's style guide, source-pull policy, abbreviation conventions, or editorial judgment. The tool should reduce repetitive mechanics and improve the review record, not erase the editor's role.",
        ],
      },
    ],
    faq: [
      {
        question: "Can AutoCite process footnotes?",
        answer:
          "The document pipeline preserves supported DOCX footnotes and endnotes as separate blocks and retains Markdown note identifiers. Complex Word layouts may not round-trip pixel perfectly.",
      },
      {
        question: "Can a journal self-host AutoCite?",
        answer:
          "Yes. AutoCite is open source and supports local desktop, MCP, and authenticated HTTP deployment patterns. The deployment must still follow the repository's security guidance.",
      },
      {
        question: "Does it replace source pulling?",
        answer:
          "No. Editors still need official or authoritative sources, quotation review, pincite confirmation, and any required source-pull process.",
      },
    ],
  },
  {
    slug: "law-firms",
    title: "Private legal citation checker for lawyers and law firms",
    h1: "Review filing citations locally, with an audit trail instead of a rewrite.",
    description:
      "A local-first legal citation checker for briefs, motions, pleadings, and memoranda that preserves attorney work product and exposes every supported change.",
    lead:
      "AutoCite is designed for legal teams that want citation assistance without sending full documents to a general-purpose cloud model. Standard review stays local and every proposed edit remains inspectable.",
    asideTitle: "Built for constrained automation",
    asideBody:
      "Safe mechanical fixes can be applied. Source support, treatment, authority weight, and litigation judgment remain outside automatic approval.",
    sections: [
      {
        title: "Use a purpose-built review boundary",
        paragraphs: [
          "The application separates citation mechanics from the legal conclusions a filing depends on. That makes it easier to adopt as a reviewer-assistance layer rather than an autonomous legal-writing system.",
        ],
        bullets: [
          "Local document sessions and revision-safe autosave.",
          "Exact issue spans, provenance, and accept or reject decisions.",
          "Practitioner-focused Bluepages workflow and jurisdiction profiles.",
          "Reviewed DOCX, PDF, Markdown, and TXT exports.",
        ],
      },
      {
        title: "Optional source retrieval is explicit",
        paragraphs: [
          "When a CourtListener token is configured and deep review is requested, extracted case citations may be sent to CourtListener for matching and opinion retrieval. AutoCite labels that network boundary and does not treat later-citation counts as a citator conclusion.",
        ],
      },
      {
        title: "Evaluate it like legal infrastructure",
        paragraphs: [
          "The repository publishes deterministic evaluations, rule coverage, security defaults, packaging manifests, and limitations. Firms should still conduct their own technical, confidentiality, supervision, and professional-responsibility review before production adoption.",
        ],
      },
    ],
    faq: [
      {
        question: "Does AutoCite create an audit record?",
        answer:
          "Yes. Reviews retain structured issues, decisions, revisions, provenance, and exports. AutoCite can also generate a bounded certification-style report describing checks performed and not performed.",
      },
      {
        question: "Can it determine whether a case is good law?",
        answer:
          "No. AutoCite is not a licensed citator and does not make good-law or treatment conclusions.",
      },
      {
        question: "Can a firm deploy the MCP server internally?",
        answer:
          "Yes, with authentication and the repository's hosting safeguards. Non-loopback binding requires explicit remote enablement and an API token.",
      },
    ],
  },
  {
    slug: "privacy",
    title: "Private and offline legal citation checking",
    h1: "Your draft should not become training data, telemetry, or a mystery network request.",
    description:
      "Understand AutoCite's local-first architecture, no-telemetry application policy, optional network boundaries, and secure deployment defaults.",
    lead:
      "AutoCite treats privacy as an architectural boundary. Standard desktop review runs through a bundled local backend, and the application does not collect document analytics or usage telemetry.",
    asideTitle: "Local-first is not the same as never-networked",
    asideBody:
      "Release downloads, optional model setup, and explicit deep source review may use the network. Each boundary should be understood before confidential work is processed.",
    sections: [
      {
        title: "What stays local during standard review",
        paragraphs: [
          "The desktop application launches an authenticated loopback sidecar on the user's computer. Document sessions, revisions, citation findings, and review decisions are stored locally. The webview bridge accepts only constrained local application paths.",
        ],
        bullets: [
          "No application telemetry or document analytics.",
          "Random local port and unique launch token for the desktop sidecar.",
          "Source documents remain separate from working revisions.",
          "Browser Citation Risk Scan runs entirely after page load.",
        ],
      },
      {
        title: "Optional network features",
        paragraphs: [
          "Deep source review can contact CourtListener when the user configures a token and explicitly requests the feature. Model installation may require a deliberate download during setup, but ordinary review does not silently fetch weights.",
        ],
      },
      {
        title: "Hosted deployments require authentication",
        paragraphs: [
          "The MCP server binds to loopback by default. Remote binding requires both an explicit allow-remote setting and an API token, preventing an accidental unauthenticated public endpoint.",
        ],
      },
    ],
    faq: [
      {
        question: "Does the free browser scan upload text?",
        answer:
          "No. Its rule engine is bundled with the page and runs in the browser. The share action includes only issue counts and categories.",
      },
      {
        question: "Does the desktop app contain telemetry?",
        answer:
          "The application is designed without usage telemetry. Users can inspect the open-source code and network boundaries in the repository.",
      },
      {
        question: "Can I use deep review with confidential work?",
        answer:
          "That is a legal and organizational decision. Deep review sends extracted citations to CourtListener and should be enabled only under an approved confidentiality and security policy.",
      },
    ],
  },
  {
    slug: "methodology",
    title: "How AutoCite reviews legal citations",
    h1: "Deterministic where possible. Explicitly uncertain where necessary.",
    description:
      "Learn how AutoCite extracts citations, preserves document structure, validates exact spans, builds citation graphs, and limits automatic corrections.",
    lead:
      "AutoCite combines deterministic citation extraction and rules, document structure, conservative relationship resolution, optional local model suggestions, and explicit source-review boundaries.",
    asideTitle: "The deterministic layer stays authoritative",
    asideBody:
      "A local model may classify or propose, but an automatic edit remains eligible only when it satisfies the product's deterministic safety contract.",
    sections: [
      {
        title: "1. Parse the document without flattening everything",
        paragraphs: [
          "DOCX, searchable PDF, Markdown, and TXT are converted into a DocumentIR that retains blocks, note identifiers, page evidence, and source locations where the format provides them.",
        ],
      },
      {
        title: "2. Extract citations and build relationships",
        paragraphs: [
          "AutoCite identifies supported citation spans and builds a document-wide citation graph. Conservative authority identities connect full citations, short forms, notes, and candidate antecedents while preserving ambiguity.",
        ],
      },
      {
        title: "3. Classify correction risk",
        paragraphs: [
          "Findings carry correction levels. Only safe_auto_fix items can be applied without approval. Review-required and unsupported questions remain visible rather than being converted into polished guesses.",
        ],
      },
      {
        title: "4. Validate the original span before editing",
        paragraphs: [
          "Before a correction is applied, AutoCite confirms that the source text at the recorded offset still matches the reviewed citation. Stale spans are rejected to prevent edits from landing in unrelated prose.",
        ],
      },
      {
        title: "5. Publish what was and was not checked",
        paragraphs: [
          "Rule coverage, evaluation data, source-review limitations, jurisdiction profiles, and packaging boundaries are maintained in the repository. The product uses narrow labels such as mechanically clean and source matched rather than broad legal conclusions.",
        ],
      },
    ],
    faq: [
      {
        question: "Does AutoCite use AI?",
        answer:
          "AutoCite has an optional local small-model layer, but deterministic validation remains in control of automatic edits. Standard rule-based review does not require the model.",
      },
      {
        question: "How are ambiguous short forms handled?",
        answer:
          "AutoCite resolves them only when the document graph supports a conservative relationship. Otherwise it returns bounded candidates and a review warning.",
      },
      {
        question: "Where are the evaluations?",
        answer:
          "The public repository contains deterministic gold data, document-level safety evaluations, rule-coverage artifacts, and CI commands used during releases.",
      },
    ],
  },
  {
    slug: "faq",
    title: "AutoCite frequently asked questions",
    h1: "What AutoCite can check, what stays private, and what remains your judgment.",
    description:
      "Answers about AutoCite privacy, Bluepages and Whitepages coverage, document formats, source review, local models, licensing, and limitations.",
    lead:
      "The most important product questions are not hidden behind a sales form. AutoCite is open source, and its public documentation is designed to make adoption boundaries inspectable.",
    asideTitle: "Start with the limits",
    asideBody:
      "AutoCite is a citation-review assistant. It is not an official style manual, licensed citator, source-pull service, or substitute for legal judgment.",
    sections: [
      {
        title: "Product and installation",
        paragraphs: [
          "The simplest path is the latest desktop release for Windows, macOS, or Linux. Developers can also use the MCP server, CLI, or authenticated HTTP deployment. The repository remains the source of truth for current artifacts.",
        ],
      },
      {
        title: "Coverage and accuracy",
        paragraphs: [
          "AutoCite applies only supported deterministic checks automatically and publishes known gaps. A clean result means no remaining issue detected within that supported scope, not that every possible citation rule or legal question has been resolved.",
        ],
      },
      {
        title: "Privacy and network access",
        paragraphs: [
          "Standard desktop review is local-first and has no application telemetry. Deep source review, hosted deployments, release downloads, and optional model setup have explicit network boundaries documented separately.",
        ],
      },
    ],
    faq: [
      {
        question: "How much does AutoCite cost?",
        answer:
          "AutoCite is open-source software under the MIT License. Users are responsible for any infrastructure, optional API, or organizational deployment costs they choose to add.",
      },
      {
        question: "Does it support scanned PDFs?",
        answer:
          "Image-only PDFs return an OCR-required status rather than silently pretending the document was reviewed. Run OCR first, then review the searchable result.",
      },
      {
        question: "Can AutoCite modify my original file?",
        answer:
          "The application keeps the imported source separate and writes reviewed exports or working revisions rather than silently overwriting the original.",
      },
      {
        question: "Is the local model required?",
        answer:
          "No. Deterministic review is the normal path. The optional local model is used only for bounded suggestions and does not control automatic edits.",
      },
      {
        question: "Can I audit the implementation?",
        answer:
          "Yes. The source code, tests, workflows, evaluation data, coverage artifacts, and release packaging are public on GitHub.",
      },
    ],
  },
];

export function getAudiencePage(slug: string): AudiencePageData | undefined {
  return audiencePages.find((page) => page.slug === slug);
}
