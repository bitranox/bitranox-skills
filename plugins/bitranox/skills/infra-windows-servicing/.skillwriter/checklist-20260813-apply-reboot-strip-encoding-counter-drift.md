# skill-writer checklist - infra-windows-servicing (2026-08-13, apply reboot, strip encoding, counter drift)

Integrates eight measured findings from repairing six Windows 11 25H2 guests on one host. Three
are load-bearing enough to test behaviourally; the rest are integrations into sections that
already exist.

## Scenario selection

RED arms were chosen by damage prevented, not by coverage:

| Arm | Finding                                      | Damage a reader avoids                         |
|-----|----------------------------------------------|------------------------------------------------|
| A   | interrupted apply; NewOS gone after a revert | a completed in-place upgrade reverted entirely |
| B   | strip pass through an ASCII layer, no gate   | the mirror empties the live OS                 |
| C   | live counter drift read as an escape         | a good machine restored over a clean delete    |

Findings integrated without their own arm: the `wmic` empty return, the deleted monitor, the
wrapper-verdict rule, and the third duration measurement. Each extends a section that already
carries its topic and none inverts a decision on its own.

## Contamination check

`redcheck --scenario <arm> --corpus <shipped skills> --corpus <this machine's memory store>`,
run twice: once with the skill under test in the corpus, once without.

With it in, all three arms flagged it as the top hit. That is topic-vocabulary overlap by
construction - the arm deliberately HANDS the agent that text - so the informative run is the
second.

- Arm A: exit 1, STRONG. Top hit is a memory fact on this machine (16%) sharing the lesson's own
  distinctive terms (`bootsequence`, `rueckgaengig`, `vorgenommene`). Genuine inherited coverage.
- Arm B: exit 1, but the top non-self hit is 11% on generic words (`carry`, `deleting`,
  `powershell`, `rewrite`). Nothing in the corpus teaches the encoding failure or the re-count
  gate. Read as a false positive on shared vocabulary.
- Arm C: exit 1, same shape - top non-self hit 15% on `comparison`, `counter`, `counts`,
  `judgement`. Nothing teaches counter drift.

Arm A's contamination is real, so its load-bearing evidence is a text check of the artifact,
which inherited context cannot affect: the published SKILL.md contained 0 occurrences each of
`shutdown /r`, `bootsequence`, `NewOS` and `re-arm`. It stated no rule about where the apply
reboot is issued from. The behavioural arm was run anyway and failed honestly regardless (below),
which is the stronger result.

## RED - against the published text

Each arm invoked the installed skill, verified byte-identical to the repo copy at that commit.

**Arm A failed on Q1 and Q2.** It chose the in-guest reboot and named the skill's own line as its
reason:

> "`shutdown /r /t 0 /f` ... I'd take this route, not a host-side power action ... The skill lists
> 'hard-stopping a guest mid-update' as a common mistake and the exact way component stores get
> damaged in the first place - so `qm stop <vmid>` + `qm start <vmid>` ... are both off the table
> here."

That is the defect exactly: the existing red flag against a hard stop was read as an argument for
rebooting from inside, which is the action that discards the upgrade. On Q2 it never checked
whether `NewOS` still existed; it routed into the "the update fails and rolls back" diagnostic
order, which cannot show anything for this failure. Its own gaps list named the hole:

> "The skill's only guidance on host-side power control is negative ... it never names the correct
> positive host command."

**Arms B and C did not fail.** Both scenarios telegraphed: B asked the agent to account for a
48-versus-51 discrepancy it would not have had, and C supplied a healthy-peer sample that
establishes the noise floor. Recorded as a result, not escalated until something broke. Their
value was the gaps both returned, each naming a real defect:

> B: "it never describes or warns against generating an intermediate `.cmd` batch file first ...
> Its 'batch tools abandon the whole walk at the first bad entry' warning is written about a
> single monolithic recursive command; a generated file of N independent per-item `rd /q` lines
> doesn't fail that way - it can drop items scattered through the run instead, a different failure
> shape the skill doesn't name."

> C: "The skill's own verification snippet contradicts its own monitoring guidance, and never says
> which one governs here."

## GREEN

Arm A re-run against the new text flipped on all three questions: the hypervisor stop/start with
the reason quoted, `qm stop` refused, the `NewOS` existence check run FIRST on Q2 and `bcdedit`
left alone once it returned RERUN, and on Q3 nothing staged on the guest at all. It also
distinguished an unreachable guest from a negative unprompted:

> "If the `ssh` call itself fails to connect ... I report `UNREACHABLE`, not 'not armed'".

Quote-back on the seven contested points from B and C returned a governing quote for every one,
no NONE. Q5 confirms the contradiction C found is now read as scoped rather than conflicting.

## GREEN gaps - closed or declined

- CLOSED: the rollback section said to re-run without saying when re-running is wrong. Now states
  the re-run helps only if the reboot was the cause, and where to look when it was not.
- CLOSED: the tolerant counter row gave a comparison but no verdict, leaving a within-tolerance
  move as a judgement the reader still had to make. Each row now returns a verdict, and a `PDf`
  move inside the tolerance is stated as NOT an escape.
- DECLINED: no wait interval or timeout before `qm start`. The text already directs a wait on the
  `stopped` signal, and a quoted interval would violate this skill's own rule against unmeasured
  figures.
- DECLINED: no cmd-native hex-to-decimal one-liner for `UBR`. Both measured values are given in
  hex and decimal, so the requirement is unambiguous; the conversion is the reader's tooling.
- DECLINED: silent on SSH mechanics for reaching the guest - owned by `bitranox:compuse-ssh`.
- DECLINED: no poll interval for the watch loop, same reason as the `qm status` wait.
- DECLINED: `Test-Path C:\Windows.old` is not asserted after the delete. Real, but outside the
  measured findings this change carries.
- DECLINED: the strip enumeration is directory-scoped and does not address file-typed reparse
  points. Pre-existing, unmeasured here, and inventing coverage would misrepresent it as tested.
- DECLINED: `[System.IO.Directory]::Delete(path, false)` is not a row in the measured fixture
  table. Correct, and the table was left untouched; the code comment states the equivalence to
  `rd /q` as reasoning, and no measured claim was attached to it.

## Checks

- [x] RED run against the PUBLISHED text, byte-verified against the repo copy, recorded verbatim
- [x] Inherited-context checked with `redcheck` for all three arms, both with and without the
      skill under test in the corpus; arm A's real contamination recorded and its load-bearing
      evidence replaced with a text check of the artifact
- [x] Arms that did not fail are reported as such, not escalated until something broke
- [x] Every arm asked for a `Skill gaps` section; every item closed or declined with a reason
- [x] GREEN diffed against RED in both directions; no baseline result was lost, and the one
      section RED reached correctly (the "update fails and rolls back" order) is still reached,
      now with a pointer saying when it does not apply
- [x] Each fix verified by quote-back; seven of seven returned a governing quote, none returned NONE
- [x] Every figure is the measured one; no number rounded, extrapolated or invented
- [x] Findings integrated into existing sections; one subsection added under "Choosing the remedy",
      where `/noreboot` was already documented, rather than a new chapter per finding
- [x] The self-contradiction between the monitoring tolerance line and the blast-radius counters
      is resolved by scoping, not by deleting either
- [x] ASCII only; German strings written ue/ae/oe. Verified: `grep -nP '[^\x00-\x7F]'` no matches
- [x] No hostnames, addresses, VM ids or private paths; drive letters, generic `<user>` and
      `<vmid>`, link targets and build numbers only. Verified by pattern scan
- [x] Frontmatter description extended with the rollback trigger; trigger map rebuilt
- [x] Version bumped MINOR: behaviour-changing guidance added to a published skill

## CORRECTION after the RED/GREEN (2026-08-13, same day)

Finding A shipped in this change as a RULE - "do the apply reboot from the hypervisor, not from
inside the guest" - and that is WRONG as general guidance. The behaviour it rests on (an in-guest
`shutdown /r` tearing the VM down instead of restarting it) was a TEMPORARY condition on the one
host these six guests live on, and the operator confirmed the same day that guest-initiated reboots
work there again. It is not a Windows-servicing fact and it is not a property of VMs.

The RED/GREEN above was run honestly and Arm A did fail against the published text. But it tested
the wrong premise: what it recorded as a failure - the agent choosing an in-guest reboot - is the
correct action on any platform where that reboot works. A well-executed test cannot rescue a false
finding, and this is the shape to watch for: ONE incident, evidence that fits it exactly, and a
rule generalised from a single host.

What survives, and is what the section now says:

- an interrupted apply reverts the WHOLE upgrade, not just the interrupted step;
- `[Setup360Result]=[0x0]` in the down-level's Panther log is the diagnostic - it says the
  down-level SUCCEEDED, so a revert carrying it means the APPLY was cut off and the reboot is what
  to investigate, not the upgrade;
- a rollback DELETES `$WINDOWS.~BT\NewOS`, so re-arming the boot entry boots into nothing (this one
  is real Windows behaviour and is independent of how the reboot happened);
- whatever reboot is used must genuinely restart the guest rather than tear it down mid-write -
  written as a property of the platform to verify ONCE, not as a prohibition;
- never a HARD stop mid-servicing, unconditionally.

Edits made for the correction: the section heading (now "An interrupted apply reverts the WHOLE
upgrade"), its opening paragraphs, the false-signals row, the "settle WHY it reverted" paragraph,
the red flag, the cross-reference under "A clean health check", and the CHANGELOG entry. Swept with
a matcher proven against a known positive first - an earlier sweep used `fgrep` with `\|`
alternation, which is a fixed-string match that could not fire.

NOT re-run: the RED/GREEN arms against the corrected text. The correction REMOVES a prohibition
rather than adding one, so the failure mode it could introduce is a reader doing nothing special -
which is the pre-existing behaviour, not a regression. Re-testing is worth doing if this section is
touched again.

## GREEN re-run against the FINAL wording (2026-08-13)

The correction above was made after the original GREEN, so the shipped subsection had not been
tested as written. Re-run with an inert text-only agent, same shift-log framing, four questions,
and the excerpt as the only input:

- Q1 (what next): chose the hypervisor stop/start, and gave the reason as not knowing this
  platform's behaviour - the cautious default without treating it as a rule.
- Q2 (revert with 0x0): read it as the down-level having succeeded and the apply cut off; next
  check was WHY, including whether a guest reboot tears the VM down here.
- Q3 (bcdedit shortcut): refused it, cited NewOS being deleted, ran the winload.efi gate to RERUN.
- Q4, the load-bearing one ("a colleague says you must NEVER reboot from inside the guest - is
  that what this says?"): answered NO and quoted the deciding sentence verbatim, "NOT a general
  rule that in-guest reboots are unsafe".

So the rescoped text does not read as a prohibition and a reader can point at what says so.

GREEN gap closed: it noted the text tells you to verify a platform property but never how. Added
the VM PROCESS identity check across an ordinary in-guest reboot - same hypervisor process means a
real restart, a new one means a teardown - with the instruction to do it once, in advance, on any
guest. That was the signal actually used to diagnose the original incident.

Gaps declined: the excerpt not naming the hypervisor (the text gives the Proxmox form explicitly
and the surrounding skill is platform-neutral by design), and what to read in Panther when the
reboot was already clean (that is the general Panther material, not this failure).
