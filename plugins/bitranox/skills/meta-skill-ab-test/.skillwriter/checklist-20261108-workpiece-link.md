# Review checklist 2026-11-08: [workpiece] link and the pretty-printed envelope (meta-skill-ab-test)

Change: `[workpiece] link = [...]` names gitignored workpiece paths (a vendored protoc) that
`abarm.link_paths` symlinks into every arm's worktree right after `make_worktree`, before the
session; `result.json` gains `linked`. The profile validates each entry (relative, inside the
workpiece also through symlinked parents, not in `.git`, no duplicates); `seal` refuses an entry
that is missing, tracked, not ignored, or ignored only by a dir-only pattern (checked by asking git
about a symlink in a scratch work tree, so nothing is written into the workpiece); `link_paths`
checks the ignore again in each worktree and removes its links before raising. SKELETON gets a
commented `link` line, EPILOG a `[workpiece] link` paragraph and the envelope sentence; SKILL.md
gets one paragraph after the `suite_from` one and the envelope sentence in the intro. Existing
score and result keys are unchanged. The description is untouched.

## Claims and their evidence

- [x] Description unchanged (no frontmatter line in the diff); SKILL.md, the scripts and the
      tests are ASCII only (non-ASCII byte scan printed nothing).
- [x] RED, code: on the old source 24 of the new tests failed (`AttributeError: module 'abarm'
      has no attribute 'link_paths'`, `'Workpiece' object has no attribute 'link'`, `DID NOT
      RAISE ProfileError`, seal exit 0 instead of 2, the floor's gate rc 1 for want of the
      linked protoc). `mutation_arm.py --revert` of abarm.py, abtest.py and abprofile.py to HEAD
      reports KILLED for
      `test_a_linked_prerequisite_reaches_the_arms_floor_and_survives_prune_run` (gate rc 1).
- [x] Control: `test_without_the_link_the_same_gate_fails` runs the same gate with no link and
      records `passed: False`, `linked: []`, so the gate really depends on the link.
- [x] Mutation battery (`mutation_arm.py --battery`, baseline green first and last), all 16 arms
      KILLED: no ignore check in the worktree, links kept after a refusal, an existing path
      overwritten, a missing source linked, the arm never links, seal skipping the missing /
      tracked / symlink check, seal deciding with `-v` (a negated pattern then counts as
      ignored), seal judging the directory's pattern instead of the symlink, no `.gitignore`
      copies in the scratch probe (nested `third_party/.gitignore`), seal ignoring links, and the
      four profile checks (escape, `.git`, duplicates, not parsed).
- [x] A first seal check read the deciding pattern of the DIRECTORY (`check-ignore -v`); a
      tracked `.gitignore` with `.packages/` beats `/.packages` in info/exclude there, so it
      refused a setup that works in the arm. Replaced by the scratch symlink probe;
      `test_seal_accepts_a_link_git_ignores_as_a_symlink_and_the_arm_gets_it` covers that layout
      and a nested `third_party/.gitignore`.
- [x] Executed, not reviewed: a live fake-claude arm with the link passes a gate that needs
      `.packages/protoc/bin/protoc`, saves no `untracked.tar`, and `prune-run` leaves the
      workpiece's real `.packages` intact; under the fake bwrap the session argv names no
      `.packages` path (no new bind; the fake's ARITY table needed no new option).
      `prune` with the link listed as a cache path removes the link and keeps the target.
- [x] Windows: the e2e and seal tests use `scratch_repo`, which skips on Windows (the harness is
      Linux only); the profile symlink-escape test uses it too.
- [x] Full suite with CI's dependency set: 401 passed, 1 skipped.
- [x] RED, text: the opus `baseline-probe` run for the previous change (pre-edit SKILL.md) already
      held this change's two questions and answered NONE to both: it guessed a read-only link and
      `PROTOC` for the directory question and `json.loads` of the whole stdout only from "tree
      convention" for the envelope question.
- [x] GREEN (opus x1, haiku x1, five questions: give arms the directory, parse `--json`, a
      `.packages/` gitignore line, a write under `sandbox = "none"` and after the cleanup, check an
      arm got it): every answer a direct quote.
- [x] Gaps from GREEN, decided:
  - CLOSED: what `linked` holds and where (both) - "the arm's `result.json` lists the entries
    under `linked`".
  - CLOSED: whether the `.packages/` line must go (both) - "the `.packages/` line may stay", made
    true in code by the scratch symlink probe above.
  - CLOSED: re-run seal after the fix (both) - "and run `seal` again".
  - CLOSED: who removes the worktree (both) - "which each arm does at its end" (`_cleanup` in
    `scripts/abtest.py` calls `abarm.prune`).
  - CLOSED: bwrap-host-proc too (opus) - "under either bwrap kind".
  - CLOSED: nested paths, relative to what (opus) - "relative to the workpiece root;
    `third_party/protoc` works too".
  - CLOSED: missing at seal or at run time (opus) - "An entry gone by an arm's start fails that
    arm before its session" (`_link_one` raises before `dispatch`).
  - DECLINED, outside this paragraph: the `env_keep` syntax and which other variables a build
    needs (the profile key is the reader's own build's business), and how a build that writes into
    the read-only link is classified (the score paragraph's `gate=`/`suite=` rules apply).
- [x] Re-probe on the revised text (haiku, six questions on the closed gaps): every answer a direct
      quote. Its leftover gaps are DECLINED: which `.git/info/exclude` in a worktree setup (the
      workpiece's own, the only one the reader edits), the refusal's exact text and exit code (the
      intro states exit 2 for could-not-run), whether `seal` records the entry set (the profile is
      sealed whole), and the string format of `linked` ("the entries" as written in the profile).
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion point (the run dir paragraph) holds no back-reference that now binds to it.
- [x] Decisions: none - the field, its checks and its documentation follow the approved plan; the
      dir-only refusal and its exact symlink probe close a defect (an unignored link an agent
      would commit), they do not choose between options.
