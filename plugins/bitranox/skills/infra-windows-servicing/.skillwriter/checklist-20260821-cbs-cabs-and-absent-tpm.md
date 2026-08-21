# skill-writer checklist - infra-windows-servicing (2026-08-21, CBS cabs and the absent-TPM waiver)

Two measured findings integrated: servicing history lives in `CbsPersist_*.cab` that a grep cannot
read, and `AllowUpgradesWithUnsupportedTPMOrCPU` does not waive an ABSENT TPM.

## Scenario selection

| Arm | Finding                                         | Damage a reader avoids                                 |
|-----|-------------------------------------------------|--------------------------------------------------------|
| A   | live CBS logs span days; the history is in cabs | a provably-broken machine reported as clean            |
| B   | the MoSetup waiver does not cover an absent TPM | re-running setup and clearing `$WINDOWS.~BT` for hours |

## Contamination check

`redcheck --scenario <arm> --corpus-cascade .`, 767 documents assembled.

- Arm A: no hit on the lesson. Top hit 0.103 on a scope descriptor, then 0.086 on a sibling fact
  about repair-versus-upgrade. Read as clean, which means NOT CAUGHT rather than absent.
- Arm B: exit 1, STRONG. Top hit 0.222 is the fact that teaches exactly this lesson, present on
  this machine. Genuine inherited coverage.

Arm B's load-bearing evidence is therefore a text check of the artifact, which inherited context
cannot affect. Against the published text: 0 occurrences each of `CompatData`, `TpmVersion`,
`TpmPresent`, `tpmstate0` and `UnrecognizedCompatBlock`; `AllowUpgradesWithUnsupported` appeared
once, in a sentence claiming `0xC1900200` "is cleared by" the key - which is not merely incomplete
but wrong whenever the guest has no TPM. Arm A's text check: 0 occurrences each of `CbsPersist`,
`expand.exe` and `.cab`.

The behavioural arm was run for both anyway. Arm B's reply confirms the contamination rather than
refuting it: it asserted the skill "is explicit about what `AllowUpgradesWithUnsupportedTPMOrCPU`
does and does not cover", a boundary the published text never draws. That is the documented tell -
a quote that is not in the file it was given.

## RED - against the published text

- [x] Arm A failed honestly. The agent chose C and reasoned correctly from the size gap that a
      zero-hit grep was a missed search, then landed on the wrong artifact: "the earlier content
      migrates to `CbsPersist_<UTC-timestamp>.log` files", and planned to "grep those specifically".
      They are `.cab` archives, so that plan reproduces the original dead end. Its own gaps list
      names the cause: "I inferred CBS.log rotation into `CbsPersist_*.log` from general Windows
      servicing knowledge, not from anything this skill states."
- [x] Arm B passed, contaminated, evidence replaced by the text check above. It still produced one
      genuine failure worth countering: it read the faster second run as proof the appraisal never
      re-ran ("it failed sooner ... consistent with hitting a different, still-enforced gate"),
      which is the opposite of what was measured and sends the reader to clear `$WINDOWS.~BT`.
- [x] Both dispatches asked for a `Skill gaps` section; both replied with one.

## GREEN - against the edited file

- [x] Arm A re-run: chose C, quoted the new subsection, and gave the expand-the-cabs command
      verbatim, adding that it would not pipe `expand.exe` into `Out-Null` and would check
      `$LASTEXITCODE`.
- [x] Arm B re-run as quote-back: four contested questions, each answered with a DIRECT QUOTE of
      the new text, no NONE. The absent-TPM boundary, the CompatData read, the stale-vs-fresh
      timestamp and the `Out-Null` rule are all now IN the file rather than inferable from it.
- [x] RED-to-GREEN diffed in both directions. Gained: the `.cab`/`expand.exe` step neither RED arm
      reached. Lost: nothing - the size-gap reasoning and the "pull the real error code" step both
      survive into GREEN.

## REFACTOR - gaps closed or declined

- [x] CLOSED: a STALE CompatData timestamp was never explained, only the fresh case. The section
      now states what a timestamp matching the previous run means, and that clearing `$WINDOWS.~BT`
      is right only then.
- [x] CLOSED: no single ordered procedure for "0xC1900200 survives the waiver". The section now
      opens with the order and forbids re-running setup between the steps.
- [x] CLOSED: two different grep patterns for the same content, unexplained. The text now says the
      cab pattern targets the symbolic names and the live-log pattern is a numeric-code scan.
- [x] CLOSED: no day count for the live-log window, and no fallback when the expanded search is
      also empty. Both stated - retention follows servicing traffic rather than a fixed number of
      days, which is why the size gap is the tell, and an empty expanded search means the history
      for that date is gone.
- [x] DECLINED: the 20-25 GB headroom floor is not calibrated per-KB. Pre-existing text, out of
      scope for this change, and deliberately a rule of thumb.
- [x] No gap left undecided.

## Quality checks

- [x] Frontmatter parses; `name` unchanged, `description` 609 chars, trigger-first, well under the
      1024-char router cap.
- [x] Description extended with the CBS trigger and `build_skill_triggers.py` re-run. The generated
      map is unchanged: it derives ~14 keywords from the FRONT of a description, so a trigger
      appended at the end reaches the injected listing but not the derived map.
- [x] Reference/hub skill, 5591 words, allowed to exceed the 500-word body target.
- [x] No address, MAC, hostname or path added that is not a reserved documentation value; no
      internal machine identifiers. Verified with the checklist's grep - no hits.
- [x] No external doc reference added; the grep for bare package-local paths returns nothing.
- [x] Tell sweep clean.
- [x] Security scan: the change adds no credential, no private host, and no unsafe construct. The
      one added command runs `expand.exe` on a fixed system path with an argv-style loop.
- [x] Ships no scripts, so no sibling tests are required for this change.
