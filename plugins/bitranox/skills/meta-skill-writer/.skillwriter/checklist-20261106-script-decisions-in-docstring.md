# skill-writer checklist - meta-skill-writer (2026-11-06, a bundled script's decisions go in its docstring)

A new subsection after "Bundled scripts and hooks: keep them cross-platform", "A bundled script's
decisions go in its docstring, not the skill's ledger": a decision about a bundled script
(`skills/<skill>/scripts/*.py`) or a hook goes in a `Decisions:` block in that file's module
docstring (form in `bitranox:meta-claude-hooks`, `references/authoring.md`), each decision naming
the test that pins it; read the block and its tests before changing the file; the ledger holds
decisions about the skill's TEXT only, a script-only change records nothing in it, and a mixed
change's `Decisions:` line names only ledger entries. Made consistent with it: "A decision is not
a story" (a rule in the skill's text goes in the ledger, a script's or hook's in its docstring),
the REFACTOR paragraph "Record every decision the edit makes about the skill's text", and the
matching REFACTOR checklist item. Description unchanged.

Decisions: d-20261106-3b3addde

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`); Step 0b `show meta-skill-writer
      --kind rejected,removed --full` printed one live entry (d-20261106-9d417d2a, a narrative
      history file per skill); the change neither touches nor contradicts it. No anchored sentence
      changed: `skill_decisions.py check` reports 0 findings.
- [x] Not mirrored: `repo-gate.py --mirrors` lists 12 pairs, meta-skill-writer not among them.
- [x] Skill type: technique; test is application - where an editor records a decision a script
      or hook settles.
- [x] Inherited-coverage check: no memory fact body and no installed copy teaches the docstring
      rule for scripts (grep of the five memory stores for a docstring Decisions block: none;
      the installed meta-claude-hooks reference has no `Decisions:` text). Behavioural RED stands.
- [x] RED, pre-edit text (`git show HEAD:`, excerpts: "A decision is not a story", the head of
      "Bundled scripts and hooks", Step 0b, the REFACTOR record paragraph and its checklist
      item), opus x2:
  - A (script-only change to `scripts/scan.py`: a measured 30 s timeout, a regex parser rejected
    for `ast`): both decisions went into `compuse-foo/.skillwriter/decisions.jsonl`, the timeout
    as a `rule` anchored on a scan.py line; quoted "Record every decision the edit makes, in
    REFACTOR, before the commit." RED.
  - B (a PR loosening a hook's matcher, no Markdown): looked in and recorded into the skill's
    ledger; quoted "A decision is not a story ... go in the skill's decision ledger". RED.
  - Skill gaps from RED, both: which ledger owns a hook; what a `rule` anchors on when no Markdown
    changed. Both closed by the new subsection.
- [x] GREEN, edited text pasted (same excerpts plus the referenced authoring.md section):
  - opus A: both decisions in scan.py's docstring block with `Pinned by:` tests; nothing in the
    ledger; quoted the new subsection. PASS.
  - opus B: read the hook's docstring block and its tests first; the loosening recorded there with
    the replaced form as `- Rejected:`; nothing in the ledger. PASS.
  - haiku (mixed change: one SKILL.md sentence plus the two scan.py decisions): the SKILL.md
    decision to the ledger, the two script decisions to the docstring. PASS.
- [x] GREEN gaps worked:
  - Closed: "the opening paragraph overstates" (its first clause sent every decision to the
    ledger) - it now says "a rule in the skill's text".
  - Closed: what the checklist's `Decisions:` line says when a change edits SKILL.md and a script
    - names only ledger entries (a script-only change needs no checklist: repo-gate.py:1437 judges
    only changed SKILL.md files).
  - Declined, covered elsewhere: no block yet / reversing an entry / test location - the block's
    handling is in meta-claude-hooks `references/authoring.md`, "Record a decision in the module
    docstring" (the pointer is in the new subsection); test location is "Ship tests for every
    script".
  - Declined, out of scope: a reviewer of someone else's PR (this skill is the author's
    procedure); a gate for docstring blocks (none by design, user decision 2026-11-05).
  - Declined, judgement left open: one entry or two for a chosen-plus-rejected pair.
- [x] Re-probe on the final text (haiku, typo-only SKILL.md change plus a scan.py decision):
      `Decisions: none - ...` with the parser decision in scan.py's docstring; no new undecided
      gap (remaining gaps are the authoring.md form it was not shown).
- [x] Tiers and cells: RED opus x2; GREEN opus x2 + haiku x1; final re-probe haiku x1.
- [x] No command added by this change (it adds a pointer to existing text only).
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point re-read ("Ship tests for every script" and "Write the skill and its
      artifacts" follow-on paragraphs bind as before). ASCII only; history-phrase finder: no hit.
- [x] Ledger: one `rule` entry, anchored on "The skill's decision ledger (Step 0b) holds decisions
      about the skill's TEXT only", tier `user` (user decision 2026-11-05), added with
      `skill_decisions.py add --from-file`.
