# meta-dream-tree: a level's topics hold for everything below it

Scope: `SKILL.md` step 0b, paragraph "Topics of a level": the `TOPICS:` line names the topics
that hold for everything below the directory, and a container whose children use different
stacks gets none of them (a topic every one of its two or more child levels has reaches it
through the engine's roll-up). `topic_tagging.py questions` asks the judge the same question for
a directory, pinned by
`test_a_directory_has_a_topic_only_when_it_holds_for_everything_below_it` in
`tests/test_topic_tagging.py`.

## Step 0b

- [x] `skill_decisions.py show meta-dream-tree --kind rejected,removed --full`: one rejected
      entry (d-20261106-7121104c, re-running ref_map after a dropped move). Unrelated.
- [x] `skill_decisions.py show meta-dream-tree`: no live rule anchors the edited sentences.
- Decisions: d-20261112-cffc4b77

## Ground truth for the claims

- [x] The roll-up the text names: `hooks/topic_placement.py` `_rolled_up` returns nothing for the
      top or a level with fewer than two child levels, else the intersection of every child's
      topics; `topics()` docstring: "declared there, or had by every one of its two or more child
      levels".
- [x] `redcheck --corpus-cascade` on the scenario (container with a Python and a Rust child):
      `clean - no inherited coverage, no telegraphing found` (1919 documents read).

## RED (pre-edit paragraph from `git show HEAD`), opus and haiku

Situation: list `python`, `rust`; `apps` ("a Python web service and a Rust engine") with children
`apps/web` (Python) and `apps/engine` (Rust); `--topics` per level, with the deciding quote.

- [x] opus: `apps` -> `python,rust`, quoting "a container with two stacks gets both".
- [x] haiku: `apps` -> `python,rust`, same quote. Both leaves right on both tiers.

## GREEN (new paragraph), opus and haiku

- [x] opus: `apps` -> `''`, quoting "a container whose children use different stacks gets
      neither" and "hold for everything below that directory, never one only some of its
      projects use". Leaves `python`, `rust`.
- [x] haiku: `apps` -> `''`, same container quote. Leaves `python`, `rust`.

## Gaps reported, and what was done

- [x] "neither" assumes two stacks (opus): closed, now "gets none of them".
- [x] Descriptor names both stacks, container rule says none, which wins (opus, haiku): closed,
      "even when its descriptor names them all".
- [x] "a topic its two or more child levels all have" readable as "any two" (haiku and opus on
      the second run): closed, "when it has two or more child levels, a topic EVERY one of them
      has reaches it". Re-probe on the final text, opus and haiku, `tools` with children python,
      python, go: both `''`, both answer no roll-up for python, quoting that parenthetical.
- [x] Order of tagging children and container: declined, it cannot matter - the roll-up is
      computed from the whole level map at render time (`hooks/topic_placement.py` `_rolled_up`),
      never stored on a line.
- [x] What an empty `--topics ''` prints, and failure handling when `topics updated:` is missing:
      declined, unchanged by this edit and verified for the paragraph in
      `checklist-20261112-tag-and-render.md` ("`set-level-topics` (also with `--topics ''`):
      `fresh`, exit 0").
- [x] `--proj` form, "descriptors are fresh" check, topic case matching, stack vs topic wording:
      declined, outside this edit; the paragraph's other sentences and step 0b's freshness pass
      govern them, and no probe answered any level wrong because of them.
- [x] Whether a uniform container may declare the topic itself: declined, the line's definition
      already answers it (the topic holds for everything below), and the roll-up gives the same
      placement either way.

## Final re-probe (final text), tiers and cells

- [x] 2 tiers (opus, haiku) x 3 rounds (RED, GREEN, re-probe of the roll-up wording), plus one
      seven-level round on both tiers (`apps`, `tools` with python, rust, go children): every
      container `''`, every leaf its one topic. The last round raised no new undecided gap.
- [x] Width and fence check over the added lines: no output.
</content>
</invoke>
