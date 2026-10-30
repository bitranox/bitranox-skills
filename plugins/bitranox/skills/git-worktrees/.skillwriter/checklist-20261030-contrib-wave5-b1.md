# Review checklist: git-worktrees, queued contribution (2026-10-30)

Entry covered: never create a worktree inside a directory Claude Code reads skills from; a
misplaced one cannot be moved across filesystems. New paragraph after the Safety Verification
"Why critical" line. The cross-filesystem half was ALREADY in the Quick Reference table ("Moving a
worktree to another filesystem"), so the paragraph points at that row instead of restating it.

## Evidence

- [x] `git worktree move` across filesystems, run in a scratch repo (tmpfs to ZFS): exit 128,
      `fatal: failed to move ... Invalid cross-device link`, worktree left in place - matches the
      existing Quick Reference row.
- [x] A directory directly under `~/.claude/skills/` holding a `SKILL.md` is loaded as a skill:
      the user-level `toolbox` skill (a git repo at `~/.claude/skills/toolbox/` with `SKILL.md` at
      its root) appears in this session's available-skills listing as `toolbox`.
- [x] RED as a text check on the pre-edit file: `reads skills from` 0 hits (`cross-device` 1, the
      existing Quick Reference row). After: the new paragraph present.
- [x] GREEN probe (`bitranox:baseline-probe`, haiku, excerpt pasted): asked where a worktree of a
      repo at `~/.claude/skills/toolbox` may not go, it quoted "Never put a worktree inside a
      directory Claude Code reads skills from" and "loaded as a second copy of that skill".
- [x] Skill gaps: "no safe location named" - declined: Directory Selection above the paragraph
      already gives the location order; "the excerpt referred to a Quick Reference row not shown"
      - declined: the row exists in the same file (it was the probe's excerpt that omitted it).
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion (#### Create the Worktree) was read.
- [x] ASCII only; front matter parses with `yaml.safe_load`; skill tests pass (git-worktrees and
      meta-skill-writer tests: 188 passed).
- [x] No private paths, hosts or names.
