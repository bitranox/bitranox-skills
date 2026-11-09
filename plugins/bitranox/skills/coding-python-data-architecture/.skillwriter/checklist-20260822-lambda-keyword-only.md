# skill-writer checklist - coding-python-enforce-data-architecture-strict (lambda vs keyword-only)

Change: a second worked example in "Define the types; never suppress or exclude the checker" - ruff
FBT and pyright strict collide on a lambda, and the fix is a typed nested `def`, not a suppression.

## PLAN

- [x] Skill type: discipline (strict data architecture) with worked examples. Test approach: run
      both arms through the real checker, then a text check of the artifact.
- [x] Checked against EVERY shipped skill: `grep -rn FBT plugins/bitranox/` returns NOTHING
      anywhere in the plugin, so neither the rule collision nor its resolution is documented. This
      skill owns the "define the types, never suppress" section, and the whole point of the entry
      is that the tempting fix is a suppression, so it belongs in that section rather than in a
      general Python skill.
- [x] Scope: one worked example plus one rationalization bullet, matching the shape of the
      rich-click example already there.

## RED

- [x] Behavioural RED is NOT available on this machine: `redcheck.py --corpus-cascade .` reports
      INHERITED COVERAGE naming
      `.claude-memory/facts/reference-a-lambda-cannot-satisfy-a-keyword-only-protocol-under-pyright-strict.md`
      (9 shared terms, the strongest hit of the seven). Route taken: TEXT CHECK of the artifact.
- [x] The claim was MEASURED against real pyright (strict) rather than copied from the queue entry,
      and the queue entry turned out to be WRONG on both specifics:

      form                      measured
      lambda assigned           2 errors: reportUnknownVariableType + reportUnknownLambdaType
      lambda passed as argument 2 errors: reportUnknownArgumentType + reportUnknownLambdaType
      typed nested def          0 errors

      The entry claimed 3 errors, and named the argument-position pair for an assignment-position
      example. The skill text states what was measured, including that the second rule code depends
      on where the lambda sits.
- [x] The `def` arm is a real control, not an assertion: it assigns the function to the same
      `Formatter` annotation, so pyright checks the same compatibility and reports 0.

## GREEN

- [x] Text check: the example states the collision (FBT forbids a boolean positional, so the
      Protocol goes keyword-only), the mechanism (a lambda parameter takes no annotation and
      pyright will not back-infer one), the exact diagnostics for both positions, and the fix.
- [x] Quote-back for why it is misread: "Both errors name the LAMBDA, so it reads as a pyright
      quirk rather than a consequence of the `Protocol` change."
- [x] Quote-back for why the obvious suppression is wrong, from the added rationalization row: "the
      `Protocol` types the PARAMETER the callable is assigned to, never the lambda's own
      parameters, which is why the checker cannot see them".

## REFACTOR

- [x] Added to the existing "Rationalizations that do not fly here" list rather than starting a new
      one, so the reader meets it where the other suppression excuses already live.
- [x] Closes the proportionality argument explicitly ("the `def` is the same number of lines"),
      because that is the excuse this particular fix invites - unlike the rich-click case, the
      suppression here is genuinely one comment.
- [x] Notes that a `def` is available anywhere a lambda is, including nested, which is the only
      structural objection to the fix.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Code example is minimal and runnable, and both arms were actually executed through pyright.

## Deliverables

- [x] `SKILL.md`: one worked example and one rationalization bullet. No script, so no `tests/`
      change.
