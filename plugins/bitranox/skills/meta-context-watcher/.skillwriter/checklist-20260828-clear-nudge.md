# skill-writer checklist - meta-context-watcher (2026-08-28, /clear nudge)

Step 6 named the `/clear` nudge but specified no message, so the wording was rebuilt from scratch
on every run and the "I cannot run it" half went missing while the reply still read as complete.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-context-watcher`).
- [x] Skill type: discipline. The rule governs what an agent does at a moment where continuing is
      tempting, so the test is a pressure scenario, not a retrieval check.
- [x] Two scenarios drafted: a pending trivial edit plus a fresh user question (temptation to
      continue), and a clean finish (does the nudge survive when nothing competes with it).
- [x] Scope: step 6 only. No new capability; steps 1-5 untouched.

## RED
- [x] Cascade contamination checked with `redcheck.py --corpus-cascade` over 868 documents.
      It reported INHERITED COVERAGE against the tree-top `CLAUDE.local.md`, adjudicated as a FALSE
      POSITIVE: the four shared terms are function words (changelog, final, seconds, taking), the
      word "handover" appears zero times in that file, and its single `/clear` hit teaches that
      built-in slash commands are not invocable - the mechanism step 6 already cited, not the
      lesson under test. The behavioural RED therefore ran.
- [x] RED, clean finish: the agent wrote "Type `/clear` when you're ready" - an invitation, not an
      instruction - and never said it cannot run the command, though step 6 requires saying so
      plainly. Its own gaps section asserted "I made that explicit in the reply", which the reply
      contradicts: a self-report, not evidence.
- [x] RED, pending work: the nudge was not last. A parenthetical about re-asking followed it.
- [x] Both arms reported the wording as "my own construction" / "my judgment call". No message was
      specified, so each run reconstructed one, and reconstruction is where the half went missing.

## GREEN
- [x] Both arms returned the specified line verbatim, nothing before or after it, on the same model
      and prompts as RED with only the skill text changed.

## REFACTOR
- [x] GREEN diffed against RED in BOTH directions. GREEN LOST a result: RED told the user to re-ask
      the deferred question, GREEN dropped it in total silence. Not a trade - step 5 sends the user
      back to re-ask, which fails if they never learn the question was heard.
- [x] The loss was causal rather than run-to-run variance: the agent quoted "Nothing follows it...
      not a question" as its stated reason for the silence, naming the sentence the edit had added.
- [x] Closed by routing what is owed to BEFORE the nudge, in one sentence, keeping the nudge last.
- [x] Re-tested only the arm the fix touches, not the whole skill.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description stays 260 chars, and
      `docs/skills.md` regenerates byte-identical (md5 unchanged).
- [x] Re-test result: the deferral now precedes the nudge and the nudge is last and verbatim -
      "Not answering the auth-test flake in this session - re-ask after `/clear` ..." followed by
      the specified line. Both properties hold at once.
- [x] Verified by quote-back, not paraphrase: the agent cited "A question they asked while you were
      writing is the case that matters: say you are not answering it in this session... then send
      the nudge" as the text it acted on.

## Gaps reported and DECLINED
- [x] "Is a leftover CHANGELOG chore forbidden too?" - declined, already owned by step 5 ("not even
      the next action you have just written into the file"). Every arm inferred the right answer.
- [x] "Does investigating the question count as the part-way task or a new one?" - declined; the
      agent noted the answer is the same either way, so the distinction changes no action.
- [x] "Is more than one sentence of acknowledgement permitted?" - declined by design. One sentence
      is the cap; more becomes the recap step 6 forbids.

## Open thread SETTLED: does the fixed wording get parroted when it misfits?

The verbatim template was kept on the reasoning that reconstruction was the measured failure. The
risk accepted alongside it was that an agent would emit `handover.md` when the file is elsewhere.
Tested with two arms where the bare basename is insufficient, neither telegraphing what was being
measured, against the shipped 5.268.0 text.

- [x] Nested path (`services/auth/handover.md`, with an unrelated months-old `handover.md` at the
      monorepo root, so the bare literal names the WRONG file): the agent sent
      "Handover written to `services/auth/handover.md`." Path substituted, rest verbatim, nudge last.
- [x] Two checkouts open (a worktree plus its main checkout, each with its own `handover.md`): the
      agent sent the full worktree path and added one line naming which checkout it worked in.
- [x] Control already held: when the file IS `handover.md` at the repo root, both earlier arms sent
      the literal unchanged.

**Verdict: the template does not get parroted.** 2 of 2 adapted, including the case where parroting
would have pointed the reader at another session's file. The predicted defect did not reproduce, so
no change is made - adding wording for it would be content for a hypothetical case.

**Residual, recorded not closed:** both arms reached the right answer by INFERENCE and said so.
Arm A: "'send it as written' guards against softening the `/clear` instruction, not against filling
the placeholder in with the file's real name ... this substitution is my inference, not something
the text states." Arm B: "a stricter reading would have me send the template's exact wording
unchanged." So the prose reads as ambiguous even though both resolved it correctly. Declined for
now on the evidence: behaviour is right 2 of 2, and the user's standing decision is to keep the
wording fixed. Re-open if a run is ever observed emitting the bare literal for a file that is
somewhere else.
