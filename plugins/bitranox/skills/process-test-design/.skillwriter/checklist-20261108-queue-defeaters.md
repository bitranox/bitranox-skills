# skill-writer checklist - process-test-design (2026-11-08, stand-in budgets and three defeaters)

SKILL.md gains a bullet under "Deterministic and order-independent": a budget the code spends
waiting on a stand-in that must answer is roomy, a pacing TCP stand-in turns Nagle off, and the
test never pins bytes-within-budget. references/silent-test-defeaters.md gains three entries: a
fresh-home commit test sets the commit identity in a stripped child env; a
refused-before-side-effect test asserts every sink (RED one arm per sink); a timed-wake test needs
a case only the timeout can wake. Both "Read this when" trigger lists gain the three situations.

Decisions: d-20261108-44eb8519, d-20261108-568423ae

- [x] Step 0b: no ledger existed for this skill; nothing to reverse.
- [x] RED by text check, pre-edit text: 0 hits in SKILL.md and the reference for "nagle|NODELAY",
      "_AUTHOR_|_COMMITTER_", "nothing else wakes|untimed"; "every sink|side effect" and
      "stand-in" hit only unrelated lines (a PATH stand-in, a deadline stand-in, a side-effect-free
      skip probe). A behavioural RED was not used: the probe machine's memory index already carries
      some of these lessons.
- [x] Mechanism claims checked: `socketserver.StreamRequestHandler.disable_nagle_algorithm`
      exists (False by default) and `setup()` sets `TCP_NODELAY` from it; `mutation_arm.py --help`
      lists `--timeout`.
- [x] GREEN, the bullet and the three entries pasted, opus and haiku: six tests (trickle with a
      default handler and a byte-count assertion, a 1 s vote budget flaking in full runs, a
      HOME-only commit, a zero-timeout test asserting only the origin log, 200 short items behind
      a timed wait, and a control whose budget is meant to expire). Both tiers marked T1-T5
      defective with the deciding quote and T6 fine. 2 tiers, 2 cells.
- [x] Gaps closed after GREEN: the timed-wake outcome (zero items completed, since "interrupted"
      alone is reached by the untimed wait too) and a bound on the untimed-wait arm; inherited
      `GIT_*` variables and `XDG_CONFIG_HOME` in the fresh-home env; what "untouched" means for a
      counter and a file sink.
- [x] Re-run on the final text (haiku, the three touched entries): rewrote all three tests to the
      entries, with the zero-completed outcome, the bounded arm and the stripped env. No new
      undecided gap.
- [x] Gaps declined: "outcome class" undefined (judgement per test); Nagle on the client side
      (measured only on the server side); whether 10 s is per stand-in or total (judgement); where
      the timeout lives (the entry is about code that proves a timed wake fires); fixture setup and
      API names in the probes (not the skill's subject).
- [x] Width and fence check over the added lines of both files printed nothing. ASCII only.
