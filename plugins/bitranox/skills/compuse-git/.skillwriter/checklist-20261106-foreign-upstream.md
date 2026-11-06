# skill-writer checklist - compuse-git (2026-11-06, `@{upstream}` naming another branch)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The change adds one bullet to the shared-checkout state
      check and updates the `git_state.py` paragraph, the tools block and the Hooks paragraph to
      what the code now does.
- [x] Behavioural RED not used: the lesson is already in this machine's always-loaded memory
      (the softdev fact on ahead/behind against the last fetch carries the wrong-branch `@{u}`
      case), so a probe would inherit it, and the skill is installed, so a probe could load the
      old text. Route taken: a text check against the skill file.
- [x] RED, text check of the pre-edit file (`git show HEAD:<path>`): 0 hits for
      `abbrev-ref @{upstream}`, 0 for `--fetch`; the state-check block recommends
      `HEAD...@{upstream}` with no warning that it can name another branch or be stale.
      New text: 1 hit each.
- [x] Every command the edit adds was executed: `git rev-parse --abbrev-ref @{upstream}` printed
      `origin/master` in a worktree cut from it; `git rev-list --left-right --count
      HEAD...origin/master` printed `0 0` (rc 0) and `...origin/no-such-branch` failed with rc 128;
      `git_state.py --fetch .` flagged the foreign upstream and exited 1 with the namesake absent.
- [x] GREEN: two text-only probes (opus and haiku) given the new text answered the scenario
      (branch cut from origin/master, pushed without -u, `@{u}..HEAD` says 2) correctly: the
      count is against the wrong branch, fetch, compare with `origin/feat-x` by name; `--fetch`;
      a failed fetch is exit 2; each with a quote.
- [x] Skill gaps from GREEN decided:
      - exit 0 never stated - CLOSED ("It exits 0 when every repo is in sync").
      - does "flagged" change the exit code - CLOSED ("in sync only when `origin/feat` exists and
        equals HEAD, out of sync (1) when it is absent or differs").
      - dirty tree and the exit code - CLOSED ("a dirty tree alone does not change that";
        `_main_repos` reads only `in_sync` for exit 1).
      - precedence of 1 and 2 - CLOSED ("2 wins over 1"; `_main_repos` keeps the max).
      - meaning of the rev-list columns - CLOSED (`<only in HEAD> <only on origin/feat>`).
      - no repair given - CLOSED (`git branch --set-upstream-to=origin/feat`).
      - does the guard warn or block - CLOSED ("warns (never blocks)").
      - "the count above" points outside the excerpt - DECLINED, covered: it is the
        `git rev-list --left-right --count HEAD...@{upstream}` line in the code block directly
        above the bullet.
      - `<plugin>` vs `scripts/` path forms - DECLINED, covered: "It ships ONCE, in the skill that
        owns the jigs: `skills/compuse-toolbox/scripts/git_state.py`".
      - would `push -u` have avoided it - DECLINED, covered: "`git push origin feat` without `-u`
        leaves it so".
- [x] Re-probe on the final text (haiku) answered six questions (column meaning, dirty tree,
      absent namesake, guard blocks or not, 1 vs 2 precedence, repair) with quotes; its one open
      gap (absent namesake: 1 or 2) is CLOSED by the "out of sync (1)" clause above.
- [x] Tiers: opus x1, haiku x2 cells.
- [x] Width and fence check over the added prose lines: none over 100 columns outside code
      blocks, tables and the pre-existing one-line Hooks paragraph; no fence opened or closed.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense.
- [x] Decisions: none - the text describes what the code does; the choices it rests on are in the
      `Decisions:` blocks of `hooks/git-footgun-guard.py` and `compuse-toolbox/scripts/git_state.py`.
