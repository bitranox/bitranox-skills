# checklist - the Windows.old fast path, and what it actually reclaims

Adds three measured things the skill did not carry: discard a mounted image inside the tree before
deleting, use `robocopy /MIR` from an empty directory for the bulk (keeping the per-file loop for
residue), and the byte total overstates the reclaim by two to three times because hard links are
counted once per link.

## RED

- [x] Baseline run on the real task (delete a 569,731-file `Windows.old` optimised for speed, plus
      expected reclaim, pre-checks, and duration), pinned to a weak-literal tier.
- [x] Baseline CONTAMINATION acknowledged and worked with rather than around: the probe already
      carries this skill, so it correctly produced the cheap-path-first order, the `icacls /reset`
      prohibition, the read-only check, the SYSTEM warning, and even `robocopy /MIR /MT`. A clean
      failure was not available, so the RED signal is the three places it was WRONG while holding
      all of that.
- [x] MISS 1, reclaim: it estimated "18-25 GB, most likely toward the upper half", reasoning that
      hard-link sharing "mostly affects user-profile-adjacent content". Measured 11.30 GB on that
      exact tree. It had the mechanism and the wrong magnitude, which is the more dangerous error
      because the reasoning sounds right.
- [x] MISS 2, pre-checks: its pre-check list is otherwise thorough and contains no mounted-image
      check. One of the two guests had a stale WIM mounted INSIDE the tree reporting
      `Status : Invalid`.
- [x] MISS 3, duration: "low tens of minutes" for the delete, attributing long runtimes to the
      permission branch. Measured 83.0 min with zero permission work.

## GREEN

- [x] Each miss is answered by a specific measured counter-value in the new section, not by
      restating the mechanism the baseline already knew.
- [x] Method verified by EXECUTION on two guests, not by review: both trees confirmed absent
      afterwards (`Test-Path` false), no residue (the per-file fallback reported "not needed"), and
      no mounted images remaining.
- [x] The hard-link claim was VERIFIED rather than asserted, and the verification corrected the
      first explanation. Sampling 60 files under `Windows.old\Windows\System32` found 60 of 60 with
      multiple links, but every link pointed at another path inside `Windows.old`, not into the
      live install. So the space DOES come back and the figure was merely inflated - the opposite
      practical conclusion from "shared with the live install, never reclaimable". The skill states
      the verified version.
- [x] Sampling limit stated rather than hidden: 60 files from one directory, so pervasive
      multi-linking is established, universal within-tree linking is not.

## REFACTOR

- [x] Two measurements, not one, for the inflation claim (3.05x and 2.22x), so the skill gives a
      range rather than a single number that would read as a constant.
- [x] The duration claim carries its confound: the slower guest is the VBS variant, and VBS costs
      roughly 25% CPU on this hardware, so part of the per-file gap is that rather than count alone.
      The skill says count drives it and does not claim a clean scaling law.
- [x] The per-file loop was NOT replaced. It remains correct for residue, where reporting every
      blocker is the point; the new text demotes it to that role instead of deleting guidance that
      still holds.
- [x] Two red flags added that map to the two silent failure modes: quoting a byte total as free
      space, and deleting a tree without checking for a mount inside it.
- [x] A false-signals row added for the symptom an operator actually meets first - "25 GB deleted,
      11 GB freed" reads as an incomplete delete.
- [x] ASCII only, no em-dashes or typographic tells. No session narrative, no scratch paths, no
      hostnames, addresses or VMIDs from any real machine.
