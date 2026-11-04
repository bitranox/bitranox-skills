# checklist-20261104-name-things-the-way-the-person-sees-them

Change under test: after "The parts map onto the tool", one paragraph: the question and options
name things by what the person sees or handles, never by the code's terms (field names, element
types, internal flags, `None`), with two translated examples; a word of the person's own trade
stays; a code term stays only for someone who works in the code, with what it does.

The case behind it: questions put to a user named a label element by its field state ("an image
without bitmap"), and the user had to ask what was meant.

## PLAN

- [x] Skill type: technique. The test is application: given a decision phrased in code terms,
      does the agent write the question in the person's words, and can it quote the rule.
- [x] Scope: one paragraph in "Then walk them, one at a time".

## RED

- [x] Scenario: an `Image` element whose `bitmap` is None (a picture already saved in the
      printer); decision: refuse or print the rest and warn when the printer does not list it.
      Asked for the question call and the governing line, or NONE. The telegraphing hint ("they do
      not read the code") was removed from the scenario before the arms ran.
- [x] Inherited coverage: `redcheck.py --corpus-cascade` matched on topic words; no cascade file
      states the rule (grep), so the arms can fail honestly.
- [x] RED on haiku and opus: both wrote plain words on their own but quoted NONE. The evidence is
      the missing line, not wrong output; the rule makes it binding where defaults drift.

## GREEN

- [x] New scenario on haiku and opus (a `Barcode` whose `check_digit` is None): both questions
      free of `Barcode`, `check_digit` and `None`, both quoting the new first sentence.
- [x] Both arms ended with `Skill gaps`; worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (opus): a trade word that is not a code term ("check digit"). CLOSED - one sentence keeps
      a word of the person's own trade, with that example.
- [x] GAP (opus): no test for when a person "works in the code". DECLINED - judgement of who is
      asked; the sentence already requires saying what a kept term does.
- [x] GAP (recheck): a word both the trade and the code use ("font size" as a key name).
      DECLINED - the rule already decides by what the person handles; the probe resolved it so.
- [x] GAP (both): header length, one-point lists, description length. DECLINED - pre-existing text,
      not what this change tests.
- [x] Quote-back re-check on haiku after the refactor (a `Text` element with `rotation=90`, for a
      warehouse user): code terms translated, "label" kept as a trade word.

## Quality

- [x] Description unchanged.
- [x] Added lines ASCII and within width.
- [x] No narrative, no scratch paths.

## Deployment

- [x] Version bumped with the sibling change in the same release; `repo-gate.py` before the push.
