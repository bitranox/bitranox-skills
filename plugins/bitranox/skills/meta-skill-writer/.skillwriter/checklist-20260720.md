# meta-skill-writer checklist - 2026-07-20

Change: add the "Referencing external DOCS must be INSTALL-REACHABLE" rule (in section 5, beside
"Referencing a SCRIPT") plus a Quality-Checks item + verify grep, so authors never point readers at a
package's README/docs that are stripped from the wheel or not shipped with the skill.

Skill type: reference/hub (authoring guidance).

TDD (RED-GREEN, subagent-verified on sonnet):
- [x] RED (realistic, no give-away): asked to write a "## Reference" for a library whose docs live in
      the repo `docs/`, the subagent produced bare `docs/api.md` paths, no URL - the exact
      dangling-reference bug. Real-world RED also exists: coding-python-send-mail and -pwshpy shipped
      with it.
- [x] GREEN: same prompt WITH the rule -> discovery-first (`--help`/`help()`) + tag-anchored URLs
      re-pinned to the reader's version, zero bare package-local paths.
- [x] (Noted) an over-specified first RED "passed" - re-ran realistically; the give-away masked the gap.

Checklist:
- [x] Description unchanged (body-only rule; no CSO/trigger change) - no trigger-map rebuild.
- [x] Rule states OUTCOME (install-reachable) + mechanisms (discovery / tag-anchored URL re-pinned to
      the reader's version / distilled bundle) + the NEVER (bare package-local path).
- [x] Two-rots reasoning captured (stale hard-coded tag vs fragile `blob/main`); self-sufficiency-first.
- [x] Quality-Checks checklist item + verify grep added.
- [x] ASCII only, no typographic tells.
- [x] repo-gate --ci run before commit.
