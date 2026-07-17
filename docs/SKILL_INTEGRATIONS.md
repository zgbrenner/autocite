# AutoCite Skills and Host Integrations

The six skills under `skills/` route compatible assistants to the local MCP server; they do not duplicate the rules engine. Copy or install them only where a host officially supports local skills. Otherwise use the same instructions manually.

Claude Desktop and Codex local MCP examples are under `host-integrations/`. Both launch stdio locally. Restart the host after configuration, call `health_check`, then test `review_document` with `See 42 USC §1983.`. No document leaves the machine unless external verification is explicitly enabled.

Troubleshooting: verify `autocite-mcp` is on the host's PATH, run `autocite health`, inspect redacted host logs, and keep transport `stdio`. Uninstall by removing the MCP configuration and copied skill directories; optionally remove models with `autocite models remove --model-id ID --confirm`.

Hosts without official local MCP or skill support receive no workaround. Use the CLI or desktop application instead.
