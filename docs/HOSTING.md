# Hosting and Authentication

## Private single-tenant bearer mode

For a private deployment where the client can send an `Authorization` header, set:

```bash
AUTOCITE_TRANSPORT=streamable-http \
AUTOCITE_HOST=0.0.0.0 \
AUTOCITE_API_TOKEN="generate-a-long-random-secret" \
autocite-mcp
```

Requests to `/mcp` must include:

```text
Authorization: Bearer generate-a-long-random-secret
```

`/health` remains public for container health checks. AutoCite adds `Cache-Control: no-store` to HTTP responses. The bearer token is compared using a constant-time comparison and must be supplied through environment or platform secret storage.

This mode is useful for private infrastructure and development clients that support a fixed bearer header. It is not a complete identity system: there are no per-user identities, refresh tokens, consent screens, revocation lists, or tenant-level authorization policies.

## ChatGPT and Claude connectors

If the client cannot attach a fixed bearer header, use one of these:

1. A private/secure MCP tunnel that authenticates access outside AutoCite.
2. An OAuth-aware reverse proxy or gateway in front of `/mcp`.
3. A standards-compliant MCP OAuth deployment connected to your identity provider.

Do not publish an unprotected URL for privileged or confidential legal documents.

## Multi-user production requirements

A production service should add:

- MCP-compatible OAuth authorization and protected-resource metadata;
- individual user and tenant identities;
- per-tenant rate and size limits;
- scoped CourtListener credentials or controlled shared credentials;
- TLS and secure secret storage;
- request/access-log redaction;
- no document-body logging;
- isolated caches or no caching;
- deletion and incident-response procedures;
- monitoring that records operational metadata without retaining legal content.

## Reverse proxy example

A reverse proxy should authenticate before forwarding to AutoCite and remove any untrusted inbound identity headers. It should forward only authorized requests, impose the 15 MB request limit, disable response caching, and redact authorization headers and request bodies from logs.

## Render

The included `render.yaml` prompts for `AUTOCITE_API_TOKEN`. Leave the variable unset only for a nonconfidential demonstration behind another access control. Render's public URL should not be treated as private merely because it is difficult to guess.
