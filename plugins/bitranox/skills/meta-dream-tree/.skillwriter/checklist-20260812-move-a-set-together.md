# skill-writer checklist - meta-dream-tree (down-move a citing set in one call)

Change: step 5's placement instruction now says what to do when the citer that blocks a down-move
belongs at the target too - repeat `--slug` so the set moves as one unit - and forbids reaching for
`--force` there. It lands together with the engine capability it names (`memory_engine.py move`
takes a set of slugs) and the contract text in `references/memory-backend.md`.

## Scope
- [x] The prose and the mechanism are one change. Before it, no ordering of single-slug moves could
      demote a mutually-citing pair, so the step's only stated outs were "re-point the refs first"
      or "stays" - and the refusal line itself advertises `--force`. The text is not being softened
      to match the code; the code gained the path the text now names.
- [x] Single source confirmed: the full contract (set semantics, the outside-citer refusal, the
      atomicity guarantee) lives once, in `references/memory-backend.md`, which this skill already
      requires as background. Step 5 states only the decision rule at the point of use and does not
      restate the engine's internals.
- [x] Checked the other places the move guard is described: `meta-self-improve/SKILL.md` says
      `move` guards only INBOUND refs and never the outbound ones, which stays true and is a
      different subject (that section is about the outbound blind spot), so it is left alone.

## RED
- [x] The defect is real and was measured on the shipped engine: the pair refuses in BOTH orders,
      `! refused: down-move would dangle inbound [[refs]]: fact-b at TOP` and its mirror, with no
      non-forced path between them.
- [x] A subagent given ONLY the pre-change step-5 text and the two refusals answered
      `move ... --slug fact-a --force`, then a second command for `fact-b`, and said both facts
      cannot land in one command. That is exactly the outcome this change exists to prevent: a
      forced down-move is how a ref actually gets stranded.
- [x] The probe was de-telegraphed - the scenario names neither "set" nor "multi-slug", and the
      prompt told the agent not to invent capabilities it was not given.

## GREEN - verified from behaviour, not from the text
- [x] A second, independent subagent given only the POST-change text and the same two refusals
      answered `move --from-level TOP --to-level PROJ --slug fact-a --slug fact-b` and "yes, both
      end up at PROJ in this run", quoting the governing clause.
- [x] It rejected `--force` explicitly, citing the new sentence, so the instruction changes the
      decision and not just the vocabulary.
- [x] The command the reader derives is the one the engine accepts: the same line, run through the
      real CLI against a scratch store, prints `moved fact-a, fact-b: TOP -> PROJ (down)` and the
      tree reconciler then reports `TOTAL tree problems: 0`.
- [x] The engine tests behind the instruction fail when the fix is mutated (co-mover exemption
      removed, exemption widened to any level, or the two-phase validation collapsed), so the
      capability the text promises is itself not vacuously asserted.

## REFACTOR
- [x] Gap reported by the GREEN probe: the text says "repeating `--slug`" without showing the flag
      twice, so the exact syntax is inferred. CLOSED by the contract row it points at, which spells
      `--slug S [--slug S2 ...]`; step 5 keeps the decision rule rather than a second syntax copy,
      which is where a duplicate would drift.
- [x] Gap reported by the RED probe (what `--force` does to the dangling ref) is answered by the
      new clause naming the consequence: it strands the ref.
- [x] Undecided gap list is empty.

## Quality
- [x] Actionable at the point of use: it names the trigger (the blocking citer belongs at the target
      too), the action (one call, repeated `--slug`), and the thing not to do (`--force`).
- [x] No narrative, no provenance, no machine paths.
- [x] ASCII only.
- [x] Frontmatter untouched, so the CSO description is unchanged and needs no re-review.
