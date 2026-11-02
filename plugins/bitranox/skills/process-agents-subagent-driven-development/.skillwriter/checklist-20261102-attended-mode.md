# skill-writer checklist - process-agents-subagent-driven-development (attended mode)

- [x] Change: the attended, no-subagent way of running a plan (review the plan, batches of 3, report
      and wait, finish, stop conditions, model gate) is now the "Attended Mode" section here, and
      the description and the When to Use chart route to it. "Continuous execution" names it as
      the one exception. references/example-workflow.md compares against it.
- [x] Coverage check on the pre-edit text: grep for attended, batch, checkpoint and "ready for
      feedback" found only unrelated uses (a batched question, brief files that batch).
- [x] RED, haiku and opus, pre-edit text, scenario "12 tasks, look every few tasks, no subagents":
      no text gave a batch size (both guessed 3), and Q2 report contents and Q3 plan review were
      NONE on both tiers. Both reported the "Continuous execution" and "dispatch fix subagent" lines
      as conflicting with the request. Both chose NOT to arm the gate for their own work; the
      helper's effort was NONE on both.
- [x] GREEN, haiku and opus, same scenario plus controls: every answer quoted the new section.
      Controls held on both tiers: "execute this plan, 12 independent tasks" and a new session with
      "run the plan" both chose the subagent flow, so the mode does not over-trigger.
- [x] GREEN diffed against RED: nothing RED produced is missing. Both GREEN arms newly arm the gate
      and pin opus at medium for a helper; RED's report contents and plan review were guesses.
- [x] Gaps closed after GREEN: "a failing test" as a blocker contradicted "fix a failing task
      yourself" (both tiers; dropped from the blocker list, an expected RED stated as no failure);
      "subagent rules under Red Flags" now named as not applying; later batch size ("3 tasks", not
      "the first 3"); last batch still reports and waits; arming after a resolved concern ("once
      none is open"); helper optional ("any ... you do dispatch"); "pristine" defined.
- [x] Final quote-back on the final text, haiku and opus (7 questions): each returned the governing
      sentence verbatim for first failure, second failure, expected RED, second batch size, last
      batch, arming after a concern, warnings. No new undecided gap.
- [x] Tiers and cells: haiku x3, opus x3 (RED, GREEN, final); 32 question cells across the GREEN
      and final runs (9 and 7 questions, two tiers each).
- [x] Commands executed: `skill_receipt.py start plan-execution`, `check` rc 0, `end`, `check` rc 1.
- [x] Gaps declined:
      - Tightly coupled plan with no request for checkpoints ("manual execution" undefined, RED and
        GREEN): predates this edit; routing it to Attended Mode would decide a case nobody ruled on,
        so the text stays silent and the decision goes to the partner.
      - Re-arming on a return to step 1: `start` renews the receipt, SKILL.md "expires 8 hours after
        its latest `start`".
      - Disarming an abandoned plan: the receipt expires by itself (same line), and while armed it
        only denies a dispatch with no pinned model.
      - Effort enforcement: covered by "Review dispatches" in this file.
      - "One reasonable fix attempt", when a helper is justified, a short final batch, what to
        do about warnings the work did not cause, a red suite at Finish, and resuming after a
        mid-batch stop: judgement left to the agent and its partner; the stop rule already sends the
        hard cases to the partner.
      - Probes' "sections not supplied": excerpt only; "Pre-Flight Plan Review", "Review dispatches"
        and "Red Flags" exist in this file as their own headings.
- [x] Width and fence check over the added lines: long lines are the frontmatter, the unwrapped
      "Continuous execution" paragraph that was already long, and the two indented commands. No
      fence touched in Attended Mode; no non-ASCII added.
- [x] Paragraph after each insertion read: "The Process" and "Pre-Flight Plan Review" carry no
      back-reference that binds to the new text.
- [x] Description measured with a YAML loader: 479 characters, keys name and description. It still
      lists every earlier keyword, and adds execute plan, separate session, checkpoints and batches.
- [x] Routing unverified live: this skill is installed on the probing machine, so the description
      rewrite is checked by text only.
- [x] History-line finder over SKILL.md: one hit, "your context no longer remembers creating them",
      about an agent's context and not the skill's history.
- [x] Security scan: prose and two commands already in this file; no secrets, hostnames or paths.
