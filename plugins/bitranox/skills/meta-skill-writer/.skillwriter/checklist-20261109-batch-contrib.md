# meta-skill-writer: batch of queued improvements

Rules added: probe-prompt defects (placeholder, background sentences, scoring field), headless
`claude -p` output, gate then appended check, whole-paragraph reflow and code spans, list lead-in
count, quote-back format and control, bold lead alone, shipped tool versus text, resuming after a
compaction, lossless split recipe.

Executed before GREEN:
- A headless probe with a throwaway Stop hook on `haiku`: plain `-p` printed only the hook-reply
  text; `--output-format stream-json --verbose` held the real answer as the first assistant text
  block.
- `false; test -z ""` exits 0; with the chained refusal it exits 1.
- The extended check over a planted line reports the odd backtick count; `mdwrap.py` at width 50
  splits an inline code span.

Gaps declined:
- `show` undefined and the width script absent: excerpt artifacts, defined in SKILL.md at Step 0b
  and in the Mechanical bullet.
- Rejoin-and-reflow order for a span that overflows: judgement left to the editor; the check reports
  it either way.
- "Run or grep" for a shipped tool: left open, since the right form depends on the tool.

- [x] Step 0b: `skill_decisions.py show` run for the skill before the first edit; no rejected or
      removed decision is reversed.
- [x] RED: coverage check of the pre-edit text (`git show HEAD:<path>`): every added rule's key term
      has zero hits. A behavioural RED was replaced by this text check because `redcheck
      --corpus-cascade` names the memory store and CLAUDE.md cascade as already teaching these
      lessons (rc 1, STRONG), so an agent on this machine cannot fail honestly.
- [x] GREEN: quote-back with application questions on `opus` (effort medium) and `haiku`, the edited
      text pasted inline, every dispatch ending in a `Skill gaps` section.
- [x] Every gap is closed or declined below; a decline resting on a system claim cites its source.
- [x] After the fix round the same questions were re-run on the final text on both tiers, and no
      new undecided gap appeared.
- [x] Width, fence, backtick and tell checks over the added lines printed nothing. Each list's
      introducing sentence and the paragraph after each insertion point were read.
- [x] Every mechanism claim added was checked against the code it describes.
- [x] No session narrative, private path or history line was added; the history finder's only hit
      ("no longer covering what moved") describes a test's behaviour, not the skill's past.

- [x] Decisions: d-20261108-bed752b4, d-20261108-f195c313, d-20261108-08af36f0, d-20261108-e8b598f1, d-20261108-3bed4d24, d-20261108-1833cbcc, d-20261108-e41e3c35
