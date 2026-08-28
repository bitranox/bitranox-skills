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

**Verdict: OVERTURNED - the template DOES get parroted.** The two arms above ran on sonnet only.
Re-run on haiku, a more literal tier, the worktree arm sent a bare "Handover written to
`handover.md`" for a file in a worktree while the main checkout held its own - naming the wrong
file. Its gaps section: "The skill's template nudge refers to `handover.md` without a path,
assuming one checkout per session context. I decided not to qualify the path."

- [x] sonnet, nested path: adapted. sonnet, worktree: adapted.
- [x] haiku, nested path: adapted. haiku, worktree: PARROTED.

Three of four adapted, which is why two runs on one tier read as a clean pass. Literal
template-following is a weak-model failure, so the tier that exposes it is the one the first
round did not use.

## Fix and verification

- [x] The template line now states that `handover.md` is the path slot rather than a literal, and
      that a bare basename is for the unambiguous case only.
- [x] The failing arm re-run on haiku now sends "Handover written to `rate-limiting/handover.md`" -
      a path that resolves from either checkout.
- [x] Control against over-triggering: a single ordinary checkout with no other `handover.md` on
      the machine still sends the bare `handover.md` unchanged. The fix does not turn every reply
      into an absolute path.
- [x] Residual: "the path that reaches the file from where the user is standing" is under-specified
      when two terminals are open. The arm resolved it sensibly with a relative path good from
      either. Left as judgment rather than over-specified.

## Method note for the next edit

A pass measured on one model tier is not a pass. The failure mode being tested (following a literal
template too literally) is exactly the behaviour a capable model reasons its way around, so the
arms that matter are the least inferential ones available.

## Post-fix matrix, both tiers

The fix was first verified on two haiku cells only. Completed on sonnet, the tier that writes
handovers in live sessions.

| case                              | haiku                       | sonnet                                                  |
|-----------------------------------|-----------------------------|---------------------------------------------------------|
| worktree beside its main checkout | `rate-limiting/handover.md` | `~/code/api-server-worktrees/rate-limiting/handover.md` |
| single checkout, unambiguous      | `handover.md`               | `~/code/invoice-parser/handover.md`                     |

- [x] The defect is closed on both tiers: every cell now names a file the reader can find, and the
      bare-name-for-somebody-else's-file case does not recur.
- [x] The two tiers pick DIFFERENT path forms for the same situation (relative vs absolute-from-home).
      Both are unambiguous, so the form is left to judgment rather than specified.

## Accepted drift: the control does not hold on sonnet

The over-trigger control - an unambiguous single checkout must still send the bare `handover.md` -
PASSES on haiku and FAILS on sonnet, which sends the full path. Sonnet's stated reason: a bare
basename is "technically unambiguous - but 'where the user is standing' is unstated, so I used the
full path rather than guess they're already sitting in the repo root."

Accepted rather than fixed. The failure modes are asymmetric: a longer-but-correct path is a
blemish, naming another session's file is a bug, and the wording that would restore the bare name
is the wording that produced that bug. The cost is honest and worth stating: the fixed sentence
this change was built around is not what sonnet sends in the common case, so the template is less
literal in practice than the step implies.

Re-open if the verbosity is judged to matter more than the risk, and re-run the full four cells on
both tiers if the wording is ever tightened - it has been wrong here once already.
