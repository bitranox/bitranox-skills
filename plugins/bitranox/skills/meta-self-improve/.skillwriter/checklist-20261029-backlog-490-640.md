# skill-writer checklist - meta-self-improve (backlog [490] tools, [640] worktree paths)

- [x] Change [490]: step 4 - `mcp__bitranox__memory_add` as the in-session route, its
      parameters mapped onto the CLI flags, the result envelope to require, no `--pin`
      parameter (pinned capture stays CLI), the CLI route for a session without the tool.
      Step 3b - `mcp__bitranox__contrib_add` as the in-session queue route, listing and closing
      CLI-only.
- [x] Change [640]: step 3b - a bullet: in a temporary worktree pass the MAIN checkout's path as
      `--proj`, `memory_add`'s `level` and contrib_queue's `"<cwd>"`; `git worktree list` names it;
      `contrib_add` (no path) is not used from a worktree. Step 2 case 1 points at it.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); the editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check against `git show HEAD:` of SKILL.md: `grep -c mcp__bitranox` -> 0,
      `grep -cE 'memory_add|contrib_add'` -> 0, `grep -ciE 'worktree.*(--proj|<cwd>)|(--proj|<cwd>).*worktree'`
      -> 0. Step 2 and 3b prescribed `"<cwd>"` and `--proj "<cwd>"` with no worktree case.
- [x] [640] measured, in a sandbox: HOME set to a scratch dir, a scratch tree (CLAUDE.md plus
      `.claude-memory/`), a git repo inside it and `git worktree add .claude/worktrees/wt1`.
      Output: `add ... <worktree>` and `add ... <main>` filed two queues; `list <main>` showed
      only `probe-to-main`; `queues` listed both keys, the worktree one marked `(cwd gone)`
      after `git worktree remove`; `memory_engine.py add --proj <worktree>` put the pointer in
      `<worktree>/CLAUDE.local.md` (untracked, gitignored) and the body in the tree anchor's
      `.claude-memory/facts/`; after removal no pointer remained and `--check-tree` printed
      `~ dangling body (no pointer at any level)` with `TOTAL tree problems: 0`. Isolation
      checked: the scratch HOME held both queue files, and the real queue dir's file count and
      combined digest were identical before and after.
- [x] Source check: `proj_key` hashes `os.path.abspath` (no git toplevel, no worktree mapping);
      SessionStart reads the event cwd's queue; `mod_bridge.py` runs every tool on
      `Path(os.getcwd())` and `contrib_add` has no path parameter; `memory_add` fields and the
      refusal kinds (`SlugCollision`, `HookTooLong`, `PinnedEntry`) read from register.ts and
      mod_bridge.py `REFUSALS`.
- [x] GREEN as a text check: every register.ts property of `memory_add` (7/7) and `contrib_add`
      (3/3) is named in backticks in the new text; `grep -n 'temporary worktree'` returns the
      3b bullet and the step 2 pointer.
- [x] Behavioural arms: not run - this agent may not dispatch subagents; application stays
      unverified by a probe.
- [x] Description measured: unchanged (593 chars, frontmatter not edited).
- [x] History finder over the added lines: no hit. ASCII only.
- [x] Mirror: meta-self-improve is not in the repo-gate.py --mirrors list.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
