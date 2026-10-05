# skill-writer checklist - meta-skill-writer (2026-10-05, exit-code standard 0/1/2)

render-graphs.js keeps exit 1 for a block's dot error and moves every could-not-run case and
every --combine refusal to 2; redcheck's unchecked verdict moves from exit 3 to exit 2 with
data.unchecked. The render-graphs paragraph and the redcheck sentence move with the code
(testing-skills-with-subagents.md too).

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed exit codes, answered ONLY from the pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that state the changed behaviour; no frontmatter change.
- [x] Inherited coverage: not a behavioural arm. The questions ask for the CURRENT exit codes,
      which only the pasted text can supply, so a probe answering from inherited context would
      quote text absent from the passages - none did.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q5 answered 1 for both a --combine refusal and a separate-mode dot error ("Are they
      different? No"); Q6 answered 3 and NONE for telling it from a usage error.
- [x] Skill gaps asked for: the missing codes and causes above were listed as gaps.

## GREEN
- [x] New passages pasted, same model and questions: Q5: 2 for the refusal, 1 for the dot error, "Yes, they are different", quoting
      "refuses, with exit 2" and "It exits 1 when a block has a dot error"; Q6: 2, told
      apart by `data.unchecked`, quoting "exit 2 with `data.unchecked` true".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right
      (the exit-0 cases, compare_performance's exit 2); nothing a baseline answered was lost.
- [x] Skill gaps asked for again. Closed: the probe could not tell the code of a dot error under --combine; the sentence now
      says "in either mode", which is what render-graphs.js does (a block that dot rejects
      while collecting node ids exits 1).
- [x] Every stated behaviour checked against the script it describes (its docstring, epilog or
      `main()`), and each script change is pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
