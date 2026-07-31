---
title: "How to Choose a Private Legal Citation Checker"
description: "A practical privacy checklist for evaluating legal citation software, including document uploads, telemetry, local processing, model downloads, source retrieval, and hosted MCP endpoints."
publishedAt: 2026-07-31
audience: lawyers
keywords:
  - private legal citation checker
  - offline legal AI
  - confidential legal documents
---

A legal citation tool can be accurate enough for a demo and still be inappropriate for confidential work. Privacy depends on the architecture, not merely a sentence saying that a vendor "takes security seriously."

Use this checklist before placing a brief, client memorandum, clinic file, unpublished article, or internal draft into any automated reviewer.

## 1. Does the document leave the computer?

Start with the simplest question: **Where is the document processed?**

A cloud product normally sends text or files to a remote service. A local-first product can process standard review on the user's device. Some tools combine both approaches, using local review for common tasks and a remote service for optional features.

The product should distinguish those modes clearly. "Desktop app" does not automatically mean local processing; a desktop shell can still call a cloud API.

## 2. Is there application telemetry?

Telemetry may include feature usage, document events, error reports, identifiers, or performance data. Even when document text is excluded, metadata about a matter or workflow may be sensitive.

Look for a direct answer to these questions:

- Does the application send analytics?
- Are crash reports automatic or optional?
- Is document text ever included in diagnostic logs?
- Can the network behavior be inspected?

AutoCite is designed without application telemetry. Its open-source code allows reviewers to inspect the desktop bridge, local backend, and optional network boundaries.

## 3. Are optional network features truly optional?

Legal citation products may retrieve opinions, validate metadata, download models, or connect to an AI provider. Those features can be valuable, but they should not activate silently.

A responsible product should explain:

- what information is transmitted;
- which service receives it;
- what triggers the request;
- whether the feature can be disabled;
- what the product claims after receiving the response.

AutoCite's standard deterministic review is local-first. Optional deep source review can send extracted case citations to CourtListener when a token is configured and the user explicitly requests it. The feature surfaces candidate evidence but does not make good-law or proposition-support conclusions.

## 4. How are local models installed?

A product may call a model "local" while downloading weights during the first confidential review. That creates an unexpected network event and an unreliable setup experience.

Prefer products that separate setup from review. AutoCite does not silently download model weights during ordinary document review. The optional small-model layer can be installed deliberately, and deterministic review remains available without it.

## 5. Is the local service authenticated?

Many desktop applications run a small service on the user's computer. That service should not listen publicly or accept unauthenticated requests from any local process.

AutoCite's Tauri desktop application launches its bundled backend on a random loopback port with a unique launch token. Hosted MCP deployments bind to loopback by default; remote binding requires explicit enablement and an API token.

## 6. What is stored, and where?

Ask whether the tool stores:

- the original document;
- working revisions;
- accepted and rejected issues;
- generated exports;
- source-retrieval results;
- user or organization identifiers.

AutoCite stores local document sessions and review state in a local SQLite database. The imported source remains separate from the working revision so an autosave or correction does not silently replace the original.

## 7. Can the claims be audited?

Privacy policies are useful, but architecture, tests, and release artifacts provide stronger evidence. Open-source software is not automatically secure, yet it makes specific claims easier to inspect and challenge.

Look for:

- least-privilege workflow permissions;
- dependency scanning;
- reproducible lockfiles;
- release checksums and manifests;
- documented hosting safeguards;
- explicit limitations.

## A practical adoption rule

Do not ask only whether a tool is "AI" or "not AI." Ask which exact operation runs, where it runs, what data crosses a boundary, and what legal conclusion the product claims afterward.

Read [AutoCite's privacy architecture](/privacy/) or [run the browser-only private scan](/citation-risk-scan/) to see the bounded workflow in practice.
