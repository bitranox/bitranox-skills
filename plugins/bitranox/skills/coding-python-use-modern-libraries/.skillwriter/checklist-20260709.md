# skill-writer checklist - coding-python-use-modern-libraries (2026-07-09, MCP-server row)

- [x] Change: new Quick-reference row "MCP server / client (Model Context Protocol)" picking fastmcp (decorator API, auth, composition, proxying, OpenAPI generation, built-in testing) over hand-rolled JSON-RPC and the official mcp SDK's low-level API / bundled frozen-1.0 fastmcp; description trigger list gains "MCP servers"
- [x] Vetting per the skill's own "Adding an entry" procedure: trustworthy (jlowin/PrefectHQ), common (dominant Python MCP framework), modern (2.x+ actively developed; web-verified 2026-07); no overlap with existing rows
- [x] Receipt held (skill_receipt.py, this session)
- [x] GREEN: fable retrieval test 4/4 (pick, avoid + bundled-option problem, uv install path, hand-rolled JSON-RPC rejection)
- [x] Discovery: fable routing test - MCP-server task routes here against rpyc/clean-architecture/textual/resilience decoys; rpyc decoy resisted
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md); hooks tests green
- [x] Security scan: prose/frontmatter edits only, public library names, no secrets/PII
