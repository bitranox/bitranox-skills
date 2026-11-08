# Review checklist: meta-skill-writer, Step 0b states the guard's refusal for a tool-repo twin (2026-11-08)

Change covered: two wording corrections in "Step 0b", bringing the text in line with
`skill-edit-guard.py` in this release, which hands a tool-repo twin's first edit the marketplace
copy's decision brief (`ledger_dir`, via `hooks/mirrored_skills.py`).

- The sentence saying a twin edit "gets no such refusal" now says its first edit is refused with
  the marketplace copy's list (from the marketplace checkout when reachable, else the installed
  plugin), and that running `show` for the marketplace skill name avoids it.
- `--skill-dir ... after the skill name` now reads "after the marketplace skill name".

Decisions: none - wording corrected to match the shipped guard; no rule added, removed or reversed

## Evidence

- [x] Step 0b of the procedure ran: `show meta-skill-writer --kind rejected,removed --full`
      printed one rejected entry (a narrative history file per skill); this change does not
      touch it. No live rule anchor lies in the reworded sentences.
- [x] Each claim checked against the code: `skill-edit-guard.py` `ledger_dir` returns the edited
      dir when it holds a ledger, else the marketplace copy found under `_marketplace_skill_roots`
      (the `public/KI/bitranox-skills` checkout first, then the install's own `skills/`);
      `_brief_refusal` passes that dir's name to `ran_show`, so `show <marketplace name>` is what
      counts. Pinned by `test_an_edit_of_a_tool_repo_twin_gets_the_marketplace_copys_brief` and
      `test_a_twin_edit_after_show_of_the_marketplace_skill_is_not_refused`.
- [x] RED (pre-edit text, opus and haiku, text-only probe): both answered that the guard does NOT
      refuse a twin's first edit, quoting "so an edit of a tool-repo twin gets no such refusal".
      The opus arm also could not tell which skill name `--skill-dir` follows.
- [x] GREEN (edited text, opus and haiku): both answered YES, the marketplace copy's ledger, and
      `coding-python-gitignore` as the name to pass to `show`, each with a verbatim quote.
- [x] Final re-probe after the `--skill-dir` wording fix (opus and haiku): both quote "after the
      marketplace skill name" for the name before `--skill-dir`; no new undecided gap.
- [x] Tiers: opus and haiku, three rounds (RED, GREEN, final), six cells.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion (the commit gate's anchor rule) reads unchanged and binds to nothing new.

## Gaps reported and declined (excerpt-only: the answer is elsewhere in the skill or its hook)

- What a receipt is, and whether a subagent counts as its own agent: SKILL.md "Step 0 - issue the
  session receipt", which says the guard reads the editing agent's own transcript.
- The full `show` command line: the code block at the head of Step 0b,
  `python3 plugins/bitranox/hooks/skill_decisions.py show <skill> --kind rejected,removed --full`.
- What "once" means and what the re-send does: the refusal text itself
  (`skill-edit-guard.py` `_BRIEF`: "Now re-send the edit, revised or unchanged; the re-send is not
  refused"); the per-agent, per-skill scope is the hook's docstring, owned there.
- How the guard knows a file is a twin: `hooks/mirrored_skills.py` `marketplace_name`, documented
  in the hook; the skill names the `--mirrors` listing as the reader's way to see the pairs.
- What `<marketplace>` is: Step 0b's "From the marketplace repo (or a worktree of it)" above.
  With only the installed plugin and no checkout, the refusal itself prints a runnable `show`
  command naming the skill dir it read (`skill-edit-guard.py` `show_command`, used by
  `_brief_refusal`).
- Which name fills the trailing `<skill>` of the `--skill-dir` path: both tiers filled it with the
  marketplace name in all three rounds; the path is under the marketplace's own `skills/`, which
  holds only marketplace names. Not reworded.
