# skill-writer checklist - python-layered-config (hard-linked .env, is_sensitive_at declarations)

- [x] Change: two additions for library behaviour the skill did not describe:
      1. The upward `.env` search passes over a searched `.env` with more than one hard link on every
         OS, with WARNING `dotenv_skipped_hard_link` on the `lib_layered_config` logger
         (`record.context`: `path`, `link_count`), and goes on to the next candidate; `dotenv_path=`
         loads such a file with no owner or link check.
      2. `is_sensitive_at`'s `not_sensitive` takes a `NotSensitiveKeys` or the dotted paths
         themselves; a single `str` there is refused with `TypeError`.
      The `.env` paragraph was reflowed to 100 columns, which also joins a code span
      (`--env-file <(printf 'KEY=value')`) that was split across two lines.
- [x] Step 0b: `skill_decisions.py show coding-python-layered-config` (rejected/removed in full, then
      all live entries) on a worktree at origin/master. One rejected entry
      (deploy-conflict-precedence), not touched by these passages.
- [x] Every claim executed against the library before the probes:
      - a hard-linked `.env` in `start_dir` was not loaded, one WARNING `dotenv_skipped_hard_link`
        with context `path` and `link_count: 2` reached a handler on the `lib_layered_config` logger;
      - the same file named with `dotenv_path=` loaded its keys;
      - `is_sensitive_at(("performance", "max_token_bytes"), not_sensitive=["performance.max_token_bytes"])`
        returned False, without the declaration True;
      - `not_sensitive="a.b"` raised `TypeError` ("not_sensitive takes an iterable of dotted paths,
        not a single str").
      Windows is argued, not measured: the call to the link check sits in the search loop with no
      OS gate, and its tests are `os_agnostic`.
- [x] RED: a coverage check against the pre-edit SKILL.md (`git show HEAD:`), because the lib's
      CLAUDE.md, loaded into any subagent in that repo, already states the hard-link rule, so a
      behavioural RED could not fail honestly. 0 hits each for `hard link`, `link_count`,
      `dotenv_skipped_hard_link` and a dotted-path `not_sensitive` on `is_sensitive_at`; the
      control term `dotenv_skipped_foreign_owner` was found twice.
- [x] GREEN, opus (effort medium) and haiku, the new text pasted, five questions (Windows
      hard-linked `.env` loaded?, how to load it anyway, a 0o666 single-link `.env` on Linux,
      `not_sensitive` list vs single `str`, a dotted `str` path): 2 tiers x 5 = 10 cells correct,
      each quoting the new sentences verbatim. The 0o666 question is the over-trigger control: both
      tiers still load it.
- [x] Gaps settled. Closed: the hard-link sentence did not say the search goes on, nor name the
      logger (both tiers). Declined: whether the WARNING is visible without logging set up (the same
      for the owner skip; the CLI's stderr warning paragraph covers the CLI, a Python caller owns its
      logging); how Windows reads the link count and what an unreadable count does (implementation
      detail: an unreadable stat loads the file and its read raises the usual error,
      `adapters/dotenv/default.py` `_link_count_if_shared`); the return value and optionality of
      `not_sensitive` (the signature and the "honours a declaration" clause carry it; both tiers
      answered correctly).
- [x] Re-probe on the final text, haiku, three new questions (a hard-linked `.env` with a normal one
      in the parent on Windows, the logger and context keys, a link count 3 file via `dotenv_path=`):
      3 of 3 correct, no new undecided gap.
- [x] Width and fence check on the added lines: none over 100 columns, no split code span, fences
      balanced; no non-ASCII, no history phrasing, no private path.
- [x] Decisions: d-20261117-c361e20d, d-20261117-89088ade
- [x] Mirror: the tool-repo twin `skills/python-layered-config/SKILL.md` got the same diff; from the
      first H2 on the two copies are byte-identical.
