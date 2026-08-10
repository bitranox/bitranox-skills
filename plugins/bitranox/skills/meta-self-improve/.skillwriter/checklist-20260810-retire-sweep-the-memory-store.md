# meta-self-improve: name the memory store in the contribute-then-retire sweep

Scope: one bullet in step 6's chore ladder. No code change; the behaviour lives in the skill text.

Triggered by a real incident, not a review: `gate.py` was correctly retired from the local toolbox
once it shipped in `bitranox:compuse-toolbox` (toolbox `1132eb1`, one of eight tools retired
together). The files went; one reference did not. The survivor was the memory fact prescribing
`uv run ~/.claude/skills/toolbox/tools/gate.py` in BOTH its hook and its body - and that fact is the
remedy for the tree's most-recurring shell error (recurrence 4), whose documented fallback is
hand-rolling the safe form. So the fix for the fourth recurrence set up a fifth.

## What the tests showed

- [x] RED: **DISPROVEN, and the change was cut to match.** A `bitranox:baseline-probe` given the
      UNCHANGED bullet and the real scenario answered YES - it derived the memory store from the
      existing general clause ("check what still INVOKES the local path is the operative, general
      test (not limited to its two named examples)") and listed both the hook and the body. The
      original hypothesis - that the old text put memory notes out of scope - is false for a
      focused reader, and the first draft of this change asserted exactly that. It was rewritten.
- [x] What RED DID establish, in its own Skill gaps section: "The rule never uses the word 'memory'
      or 'memory note' - it names only 'a nudge or a doc' as illustrations. A narrow, literal
      reading could miss memory notes entirely", and "No search method is specified ... doesn't say
      grep, doesn't say which directories/repos are in scope, and doesn't say how to be exhaustive."
      Those two are what the amendment now supplies. The gap is actionability, not comprehension.
- [x] GREEN: the same probe on the amended bullet answered YES and QUOTED the governing sentence
      (a paraphrase would only prove it can reason there; the quote proves the text says it). It
      independently produced the whole intended procedure: sweep the facts, fix hook AND body, use
      find because the facts and pointer blocks are gitignored, name the replacement by skill
      rather than by a versioned path, and re-grep to zero before deleting.
- [x] Evidence over verdict: the real-world outcome is the primary evidence here. A focused probe
      reaches the answer; the actual session, doing many things at once, did not sweep at all. A
      rule that is derivable but neither named nor given a method is what that difference looks
      like.
- [x] GREEN's own gap list was worked before shipping: it flagged that ordering (sweep, then
      delete) was inferred rather than stated, so "require zero hits before you delete" was added.
      Its other gaps are properties of the scenario prompt (which skill the tool landed in), not of
      the rule.

## Checks

- [x] Version bumped 5.164.2 -> 5.164.3. PATCH per this repo's own SemVer note: "backward-compatible
      fix. A bug fix, wording/doc fix in a skill" - no new skill, hook or capability.
- [x] Bump verified by re-reading `plugin.json` after the write, and the changelog entry by
      re-reading the file. A scripted bump that matched nothing and reported success shipped an
      unbumped change earlier in this same session; the script now refuses instead.
- [x] Changelog entry corrected after RED came back, so it states the disproven hypothesis rather
      than the claim the probe refuted.
- [x] ASCII only, no em-dashes or typographic tells.
- [x] Marketplace history stays append-only: normal additive commit, no squash, no force-push.
