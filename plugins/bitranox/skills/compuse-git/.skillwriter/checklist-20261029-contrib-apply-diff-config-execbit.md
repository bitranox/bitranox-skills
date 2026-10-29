# skill-writer checklist - compuse-git (six rows, exec-bit section, pathspec exception)

- [x] Change: rows for `git apply --3way`, `remote: This repository moved`, filtering a diff to
      changed lines, diffing against a moved base, `git config` from a linked worktree; the
      rev-parse ref-exists row gains the one-rev rule; the exec-bit rows, section and the
      shared-checkout pathspec rule now verify with `git ls-tree HEAD` and name the mode-change
      exception.
- [x] Mechanism claims measured in throwaway repos (git 2.53.0): `apply --3way` left
      `1 file changed` in `git diff --cached --stat`, plain `apply` left nothing staged;
      `git rev-parse --verify -q HEAD HEAD~1` printed nothing, exit 1 (without -q: 128, "Needed a
      single revision"); `git diff -U0 | grep '^[-+][^-+]'` printed nothing for a bullet edit,
      the header filter printed `-- old bullet` / `+- new bullet`; `main..HEAD` listed the
      branch's file plus a peer's later file as a deletion, `main...HEAD` only the branch's file,
      `rev-list --count HEAD..main` = 1; `git -C <wt> config demo.key x` was read back by the main
      checkout from `.git/config`, `config --worktree` landed in `.git/worktrees/<n>/config.worktree`
      and was invisible to the main checkout; with core.fileMode=false, `update-index --chmod=+x`
      plus an edit committed with a pathspec gave ls-files -s 100755 and ls-tree HEAD 100644, and
      without a pathspec ls-tree HEAD 100755.
- [x] Not reproducible locally: the GitHub "repository moved" redirect. The row asserts no outcome;
      it prescribes the ls-remote check that decides it, and set-url.
- [x] RED text check (origin/master): `--3way` 0, `repository moved` 0, `exactly ONE rev` 0,
      `'^[-+][^-+]'` 0, `git rev-list --count HEAD..<base>` 0, `worktreeConfig` 0,
      `git ls-tree HEAD` 0.
- [x] GREEN quote-back: "It STAGES what it applies (`--3way` implies `--index`)"; "`--verify` takes
      exactly ONE rev"; "Drop only the file headers"; "Diff from the merge base, three dots";
      "It writes the SHARED repository config"; "**A pathspec commit drops the mode.**".
- [x] Description: two triggers added (a push printing "This repository moved", a diff against a
      moved base); measured 303 chars with len(). Routing unverified (no probe on a machine
      without the skill).
- [x] Table re-padded by the formatter; an extra empty cell an edit introduced was removed and
      every row re-checked at two cells.
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
