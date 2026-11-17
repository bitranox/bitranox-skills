# skill-writer checklist - net-firewall-pfsense (snapshot folder inside a repo that ignores it)

- [x] Type: technique and reference. Tested with application scenarios and quote-back.
- [x] Code change first, test-driven: `prepare_snapshot_dir` refused any folder in a git work
      tree, so a site's gitignored `configs/` needed `--allow-repo-snapshot` on every change. New
      `ignored_by_git` asks `git check-ignore -- <dir>/` (index mode) and accepts only when git
      echoes the folder back; any error refuses. Before the fix 3 new tests failed (ignored
      folder, new folder below it, end-to-end `--apply`), after it all 248 tests pass.
- [x] Measured git behaviour (scratch repos): an ignored folder with nothing tracked answers
      rc 0 and names the folder; a folder holding a force-added file answers rc 1 in index mode
      and rc 0 with `--no-index`, while a NEW file in that folder reads as ignored, so the folder
      itself is asked, never a file in it. `configs/*`, `configs/**`, `/configs/` and `configs`
      all name the folder. A not-yet-existing folder needs the trailing slash to match a `name/`
      rule.
- [x] Mutations: dropping the echo check fails
      `test_prepare_refuses_a_check_ignore_that_names_no_path`; adding `--no-index` fails both
      tracked-file tests. A separate `git ls-files` check survived its own removal (index-mode
      check-ignore already refuses a folder with tracked content at any depth), so it was dropped.
- [x] Step 0b: `show net-firewall-pfsense --kind rejected,removed --full` printed nothing; the
      live list holds three unrelated rules.
- [x] RED (pre-edit text from `git show HEAD:`, opus, 1 cell): for an ignored, untracked
      `configs/` it answered "NO, refused" and "YES, `--allow-repo-snapshot` needed", quoting
      "Writing one into a git work tree is refused unless you pass `--allow-repo-snapshot`." -
      false against the new code. On the "readable by others" warning on an SMB share: NONE.
- [x] GREEN (edited text, opus and haiku, 2 cells, 5 questions): both answered YES/NO/NO for the
      ignored folder, the flag and the force-added folder, quoting the new rule sentence, and
      "do not chmod, check the share's permissions" for the warning, quoting the SMB sentence.
- [x] Diff GREEN against RED both ways: RED's own checks (check-ignore, ls-files, check that it
      arrived) remain in GREEN's answers; nothing lost.
- [x] Gaps closed from GREEN: haiku saw the first paragraph omit "nothing tracked" (now "ignores
      it and tracks nothing in it") and asked whether the warning reads the folder's or the
      files' mode (now "if the FOLDER's mode lets others read it", which is what
      `prepare_snapshot_dir` tests). Both RED and GREEN asked whether the file is dated: the name
      `config-<host>-<YYYYmmddHHMMSS>.xml` is now stated (`do_snapshot`, `strftime("%Y%m%d%H%M%S")`).
- [x] Gaps declined: a `configs/*` rule not naming the folder (measured above: it does); where
      `--snapshot-dir` sits on the command line (SKILL.md documents `--help` and both placements
      are accepted, `_mutation_flags`); whether the site rule wants a hypervisor snapshot too
      (site-specific, the paragraph already defers to the site rule); what to do if the share
      really is readable by others (a judgement for the site owner); whether a copy also stays in
      the private directory (it does not: one path is written, `do_snapshot`).
- [x] Final re-probe on the final text (haiku, 4 questions): NO flag needed for the ignored
      folder, NO write into the force-added folder, the warning reads the FOLDER's mode and the
      remedy is the share's permissions, and both paragraphs state the same condition, each with
      a verbatim quote of the edited text. Its remaining gaps are excerpt-only (the override sits
      in the second paragraph; a tracked file at any depth refuses, pinned by
      `test_prepare_refuses_an_ignored_directory_with_a_tracked_file_deeper_down`). No new
      undecided gap.
- [x] Commands executed: real `pfsense.py --help` renders the new `--allow-repo-snapshot` help;
      the end-to-end test drives `main([... --apply --snapshot-dir <ignored> dhcp rm ...])`
      against a real git with faked ssh and finds `config-192.0.2.1-*.xml` written.
- [x] Width and fence check over the added lines prints nothing; the paragraph after each
      insertion point (the next heading, the doctor code block) holds no back-reference.
- [x] Description unchanged, so routing not retested.
- [x] Cases decided beyond the report: a folder with a force-added file stays refused, and a git
      error during the ignore question refuses (the exemption fails closed).
- [x] Decisions: d-20261117-ca7cfbe2
- [x] ASCII only, present tense, RFC 5737 and /opt example values only.

## Integration correction (2026-11-17, after the code review)

- The review measured that `configs/*` plus `!configs/*.xml` made git call the folder ignored
  while `git add -A` staged the snapshot. The code now also asks about the snapshot FILE, trusts
  only a .gitignore in the checkout or `.git/info/exclude` (never a per-user excludes file),
  resolves the path first, and writes the file 0600. The paragraph "Before you change a firewall"
  was extended to say so; the anchor of d-20261117-ca7cfbe2 is unchanged. Probe: none run on
  this sentence (a factual correction of what the code does, verified by the tests named in
  tests/test_pfsense.py: negation, per_user, info_exclude, dotdot, non_ascii, owner_only).
