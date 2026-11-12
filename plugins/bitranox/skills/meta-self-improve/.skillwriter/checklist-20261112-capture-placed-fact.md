# meta-self-improve: a capture onto a fact placed by topic

Scope: `SKILL.md` step 3, two paragraphs: a fact placed by topic has a line at several levels
and no single owner; topics are never written by hand.

## Step 0b

- [x] `skill_decisions.py show meta-self-improve --kind rejected,removed --full` and `show`: no
      rejected or removed entry touches step 3's routing of an update; every live rule keeps its
      anchor (`skill_decisions.py check`: 0 findings).
- Decisions: d-20261112-307211f7, d-20261112-99839a63

## Commands run on a scratch tree (levels a, a/py, b/py, c/web; `feedback-x` bound to python,
## lines at a and b/py)

- [x] `add --proj <tree>/c/web --slug feedback-x ...`: `! refused: slug 'feedback-x' is placed by
      topic and has no line at this level; it is read at <S>/treeA/a, <S>/treeA/b/py. Write it
      from one of those levels (hooks/memory_engine.py add --proj <S>/treeA/a --slug feedback-x
      ...), or change where it is read with set-topics`, exit 2.
- [x] The same `add` with `--proj <tree>/a`: exit 0, the body and the lines at BOTH levels
      updated (hook text read back at a and at b/py); `--check-tree`: 0 problems.
- [x] `move` of it: `! refused: 'feedback-x' is placed by topic: ...`, exit 2.
- [x] `add` of a new slug whose body file carries `topics: [python]`: `! refused: 'copy-1' has
      no body file yet and the body given carries a frontmatter topics: line; topics change only
      through set-topics. Write the fact without the line, then run set-topics on it`, exit 2.
- [x] An update whose body file carries a different `topics:` line: exit 0, the stored line
      unchanged.
- [x] `add --help`: no `--force`.

## RED (pre-edit step 3), opus

- [x] `redcheck --corpus-cascade` on the scenario: clean.
- [x] The probe followed the engine's message as its only source: which level to write from
      "NOT STATED", whether the other level needs anything "NOT STATED", a topics line on a new
      fact "NOT STATED", `move` "NOT STATED".

## GREEN (new text), opus and haiku

- [x] opus: `add --proj T/a --slug feedback-x ...` with the stored title and hook; no second
      slug; nothing for the other level; no `topics:` line; neither `move` nor `set-topics`.
- [x] haiku (final text), options A-D: "Choose C: `add --proj T/a --slug feedback-x ...`,
      carrying the stored title and hook." A new slug: refused by "Do not mint a second slug for
      it." The other level: "Nothing." A topics line on a new fact: "No."
- [x] Lost results: none.

## Gaps reported, and what was done

- [x] The refusal offers `set-topics` and the text did not say whether a capture takes it
      (opus): closed, "is not a capture's to take", with what to do instead; haiku then quoted
      that sentence.
- [x] Where the stored title and hook are read (haiku): declined, the next paragraph of step 3
      says "copy them off the pointer line"; the probe was shown only the two new paragraphs.
- [x] Whether the line at the other level changes on disk (haiku): declined, measured above and
      stated as "every line of the fact, at every level".
- [x] `move` syntax, and a `topics:` line the engine might ignore (haiku): declined, neither is
      a capture's path; the refusal is stated and was run.

## Found beside the task, not changed here

- `add --proj <other level> --slug <an existing fact that is NOT placed by topic>` does not
  refuse: it exits 0, writes a second pointer line and overwrites the body, and `--check-tree`
  then reports `! duplicate pointer`. Step 3's "The level." bullet says the engine refuses that
  with `SlugCollision`. Reported to the plan's owner; the engine and that bullet are outside
  this change.

## Final checks

- [x] 2 tiers, 3 cells. Width and fence check over the added lines: no output. ASCII only.
