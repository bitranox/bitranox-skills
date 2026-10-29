# skill-writer checklist - meta-context-watcher (backlog [490]: the backlog tools)

- [x] Change: SKILL.md "Two files" - a paragraph naming `mcp__bitranox__backlog_list`,
      `backlog_add` and `backlog_close` with their parameters, what they act on (the
      `OPEN-WORK.md` at the git top level of the session cwd), that the rank stays the model's
      choice, that they take no path (a cross-repo item stays a hand edit), the ToolSearch load,
      and the hand-edit route for a session without them. Procedure step 1 also forbids
      `mcp__bitranox__memory_add` beside `memory_engine.py`.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); the editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: `git show HEAD:plugins/bitranox/skills/meta-context-watcher/SKILL.md |
      grep -c mcp__bitranox` -> 0. The pre-edit text named `backlog_close` only as a short name
      in the closing rule and never named `backlog_add` or `backlog_list`.
- [x] Source check (a quote-back proves readability, not truth): parameter names and enums read
      from `hooks/mods/register.ts` (`state` enum open/closed/all; `backlog_add` required
      rank/origin/what/size/open/next, `raised` optional, origin enum USER/FOUND;
      `backlog_close` rank/reason); target file from `open_work.backlog_path` (git
      `rev-parse --show-toplevel` of the cwd); the version floor from docs/reference.md
      "Requirement" table.
- [x] GREEN as a text check: a script extracting every property name per tool from
      register.ts found each named in backticks in the new paragraph (backlog_list 1/1,
      backlog_add 7/7, backlog_close 2/2).
- [x] Behavioural arms: not run - this agent may not dispatch subagents; routing and
      application stay unverified by a probe.
- [x] Description measured: unchanged (825 chars, frontmatter not edited).
- [x] History finder over the added lines: no hit. ASCII only; added prose wrapped to the file's
      width.
- [x] Mirror: meta-context-watcher is not in the repo-gate.py --mirrors list.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
