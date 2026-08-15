# checklist - what a dispatch costs, and how to size a fan-out by it

The "When to Use" section gains the sizing rule: an Agent-tool dispatch carries a large FIXED
token cost independent of the prompt, so a per-item fan-out is budgeted as item count times about
60k and small per-item work is batched into ONE dispatch. The skill previously described only how
to SPLIT a fan-out (partitioning, allow-lists, integration) and nothing about what each split
costs, so "dispatch one agent per independent problem domain" scaled unchallenged into a worklist
of hundreds. One "Don't use when" bullet plus one paragraph, inside the existing section; no new
chapter, and no change to the frontmatter description (so the generated catalog and trigger map
are unaffected).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`) before the first edit.
- [x] Confirmed the guidance was genuinely absent before editing. `claim_check.py --pattern
      '57\.5k|73\.4k|fixed (token )?cost|per-dispatch|60k' --control 'dispatch'` on the pre-edit
      `SKILL.md` returned ABSENT with the control matching 15 times, so the file was read. Widened
      to the whole catalogue (`--pattern '57\.5k|73\.4k|60k tokens|fixed token cost' --control
      'subagent'` over all 78 `SKILL.md`): also ABSENT, control matched 198 times across 78 files.
- [x] Checked the near misses rather than trusting the ABSENT verdict alone: `token` and `batch`
      DO occur in the pre-edit file (10 hits), every one in an unrelated sense - a test file named
      `batch-completion-behavior`, "a batch as part of a plan" for the model-gate receipt, and a
      leaked credential called a token. None is about cost, which is why the narrow pattern is the
      honest one.

## RED (route taken: text check of the artifact, behavioural arm is void on this machine)

- [x] Scenario written first, de-telegraphed (a 400-file worklist, four buckets, short per-item
      prompt, "is that design sound and roughly what should I expect it to consume"); the
      forbidden conclusion written as a separate answer file (fixed per-dispatch overhead, size by
      count times about 60k, batch instead).
- [x] `redcheck.py --scenario ... --answer ... --corpus-cascade <the dir a probe would be
      dispatched in>` reports INHERITED COVERAGE, verdict STRONG, exit 1: the corpus (619
      documents) already contains a memory fact stating exactly this lesson, so a probe dispatched
      here answers from its startup context, not from the guidance handed to the arm. redcheck's
      own recommendation is to replace the behavioural arm with a text check of the artifact.
- [x] Behavioural RED therefore NOT run as the load-bearing evidence, and not manufactured against
      a weaker scenario to force a flip. Recorded as inherited rather than escalated.
- [x] Load-bearing RED = the artifact itself: the published `SKILL.md` at the previous version
      contains no such figure and no cost rule at all (the ABSENT results above). A reader who has
      only the skill cannot arrive at the number, whatever a particular machine's context happens
      to carry.
- [x] The motivating measurement is recorded but was performed outside this change and is reported
      as such, not re-run here: an inert text-only probe asked the sizing question did not surface
      the inherited fact, answering instead from a different, skill-framed source and stating that
      no fixed per-dispatch charge is documented. That is the failure mode the edit addresses -
      guidance has to sit in the skill that frames the question.

## GREEN

- [x] Post-edit `claim_check.py --pattern '57\.5k|73\.4k' --control 'dispatch'` returns PRESENT,
      2 hits, both on the new paragraph inside "When to Use".
- [x] The new text answers the scenario directly: what the fixed cost is, what it was measured on,
      how to turn it into a budget (count times about 60k), and what to do instead when the
      per-item work is small (batch into one dispatch).

## Figures

- [x] Stated as MEASURED with the date and the subject of each measurement: 57.5k for an inert
      text-only probe with zero tool uses, 73.4k for a general-purpose agent plus one Read,
      measured 2026-08-12. Neither figure is rounded or extrapolated in the skill text.
- [x] The rule-of-thumb 60k is labelled as the sizing figure, kept separate from the two measured
      numbers, so a reader can tell the measurement from the working approximation.
- [x] No further derived figures added (no marginal-per-item cost, no payload ratio, no worked
      multiplication), keeping every number in the skill traceable to one of the two measurements.

## Scope declined

- [x] Explaining WHY an always-loaded note did not reach the moment of decision: out of scope for
      a skill about dispatching, and it would cost more lines than the rule itself. The rationale
      lives in the commit message and here.
- [x] Duplicating the tier/effort guidance already in
      `bitranox:process-agents-subagent-driven-development`: untouched. Cost per dispatch is a
      different axis from which model to pin, and the existing cross-reference already stands.

## Verification

- [x] Addition is one bullet plus one paragraph (11 added lines) inside the existing "When to Use"
      section; no new section, no restructuring, no change to any other section.
- [x] Frontmatter description unchanged, so `build_skill_docs.py` and `build_skill_triggers.py`
      outputs stay in sync (confirmed by the gate below rather than assumed).
- [x] `repo-gate.py --ci` passes on the full change set.
- [x] Version bumped MINOR, 5.200.0 to 5.201.0 (new capability in an existing skill), with a
      matching CHANGELOG entry.
- [x] ASCII only in the added text: plain hyphens, no em/en dash, no curly quotes, no ellipsis
      character (checked by scanning the changed files for codepoints above 126; the only hit in
      the repo is a pre-existing mojibake EXAMPLE in an old CHANGELOG entry, untouched).
- [x] No hostnames, IPs, usernames, private paths, session narrative or machine-specific detail in
      the skill text or in this artifact.
