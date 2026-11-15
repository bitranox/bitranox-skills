# skill-writer checklist - coding-python-use-modern-libraries (2026-11-15, MCP row for mcp SDK 2.x)

Change: the MCP server/client row. The official `mcp` SDK 2.x ships a full high-level server,
`mcp.server.mcpserver.MCPServer`, and `mcp.server.fastmcp` is gone. The Use cell now names
`MCPServer` and says when `fastmcp` still wins (ready-made auth providers, proxying, OpenAPI
generation); the Avoid cell replaces "frozen 1.0 feature set" with the removal.

- [x] Receipt held; this agent loaded meta-skill-writer itself
- [x] Step 0b: the two live rejections (httpx2 status codes, Windows bare argv0) are unrelated
- [x] Claims executed against `mcp` 2.3.0: `import mcp.server.fastmcp` raised
      `ModuleNotFoundError` with a message naming `MCPServer`; `MCPServer` exposes `tool`,
      `resource`, `prompt`, `custom_route`, `middleware`, `run_stdio_async`,
      `run_streamable_http_async`; its constructor takes `token_verifier`, and
      `mcp.server.auth.provider.TokenVerifier` imports; an in-memory
      `mcp.client.client.Client(server)` called a tool and returned structured content
      `{'result': 5}`
- [x] RED (pre-edit text, `opus` quote-back): it quoted the old row naming `fastmcp` and the
      "frozen 1.0 feature set", and its Skill gaps said nothing mentions SDK 2.x or the import
- [x] GREEN: `opus` (effort medium) and `haiku` both quoted the new Use and Avoid cells
- [x] Skill gaps from GREEN: no `fastmcp` version floor - declined, the row names no floor for
      any library and `uv` resolves the latest
- [x] Table re-checked with `reformat_tables.py`: "Unchanged", so the table stays canonical
- [x] ASCII only

Decisions: none - a table-row recommendation update; a table row cannot carry a ledger anchor, and the measurement is recorded above
