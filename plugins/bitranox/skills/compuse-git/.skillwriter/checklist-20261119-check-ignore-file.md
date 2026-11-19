# skill-writer checklist - compuse-git (2026-11-19, ask check-ignore about the file, not its folder)

- [x] Change: new section "Is a file you are about to WRITE ignored? Ask about the file, not its
      folder" after the incoming-file section: ask about folder and file in one
      `check-ignore --stdin -z -v -n` call with `core.quotePath=false`, the record layout, read
      the pattern and source fields (a `!` pattern re-includes; a source outside the work tree is
      a per-user excludesFile), and `ls-files` for what is already tracked.
- [x] Decisions: d-20261119-1aaa6968
- [x] Step 0b: the skill had no ledger entries; nothing rejected or removed to reverse.
- [x] Mechanism executed on git 2.53.0 in a scratch repo with `configs/*` plus `!configs/*.xml`:
      `check-ignore -- configs/` rc 0 echoing the folder; `check-ignore -v` on the xml file
      printed the `!configs/*.xml` rule with rc 0, plain `check-ignore` rc 1; `git add -A -n`
      listed the xml file; `-z` without `--stdin` rc 128; without `core.quotePath=false` a
      non-ASCII name came back quoted; an excludesFile match printed its absolute path as the
      source; an unmatched path under `-n` printed three empty fields and the path. The added
      snippet was run verbatim and printed the two records.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      both answered NONE for the folder-vs-file question.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: both quoted the
      new section and said the file is not safe, the exit code under `-v` is not the verdict.
- [x] GREEN gaps closed: the record layout of `-z -v -n` output and the unmatched-path record
      (added as a bullet). Round 2 on both tiers read both record kinds correctly from the text.
- [x] Declined gaps: which rule to add to keep a re-included file ignored (ordinary gitignore
      precedence, the reader's own design; not this section's question); what plain
      `check-ignore` prints for an unmatched path (the section prescribes the `-v -n` form).
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion (the next section heading) was read.
- [x] ASCII only, present tense, example values generic (`configs/`), no private paths or hosts.
