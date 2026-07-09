# skill-writer checklist - coding-python-use-modern-libraries (2026-07-09, MCP-server row)

- [x] Change: new Quick-reference row "MCP server / client (Model Context Protocol)" picking fastmcp (decorator API, auth, composition, proxying, OpenAPI generation, built-in testing) over hand-rolled JSON-RPC and the official mcp SDK's low-level API / bundled frozen-1.0 fastmcp; description trigger list gains "MCP servers"
- [x] Vetting per the skill's own "Adding an entry" procedure: trustworthy (jlowin/PrefectHQ), common (dominant Python MCP framework), modern (2.x+ actively developed; web-verified 2026-07); no overlap with existing rows
- [x] Receipt held (skill_receipt.py, this session)
- [x] GREEN: fable retrieval test 4/4 (pick, avoid + bundled-option problem, uv install path, hand-rolled JSON-RPC rejection)
- [x] Discovery: fable routing test - MCP-server task routes here against rpyc/clean-architecture/textual/resilience decoys; rpyc decoy resisted
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md); hooks tests green
- [x] Security scan: prose/frontmatter edits only, public library names, no secrets/PII

## Second change (later same session): add pwshpy row

- [x] Change: added Quick-reference row "PowerShell / Windows + OS admin objects" -> pwshpy (typed records + lazy pipeline over native OS bindings, real exceptions, memory-bounded); Avoid shelling to pwsh.exe/powershell/wevtutil/sc, raw pywin32/wmi + manual text parsing. Cross-refs the new bitranox:coding-python-pwshpy skill.
- [x] Vetting per "Adding an entry": trustworthy (bitranox public OSS), description + replaces + why all present, one line. Overlap with the Subprocess row resolved explicitly in the Use cell (pwshpy for querying/mutating OS objects; subprocess.run for launching a program).
- [x] Receipt held (skill_receipt.py, this session)
- [x] Discovery: additive reference-row edit; the skill's own description/trigger unchanged, so no discovery-behavior change to re-test
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md) alongside the new coding-python-pwshpy skill
- [x] Security scan: single table edit, no secrets/paths/PII
