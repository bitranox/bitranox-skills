# skill-writer checklist - coding-performance-review (2026-11-15, queued lessons)

Three additions to the Method: step 4 says CPU seconds are not immune to load and the before
figure belongs in the same interleaved run; new step 12 quotes a total gain from one A/B of the
original against the final code; new step 13 measures one operation's peak memory with a reset
high-water mark (the claim checker moves to step 14; nothing cites it by number). The unbounded
memory checklist item points at step 13.

Decisions: d-20261115-e918a4d0, d-20261115-b71698cd, d-20261115-852ad89d

- [x] Receipt fresh. Step 0b: `show coding-performance-review --kind rejected,removed --full`
      lists three rejected entries, all about the description and skill shape; none touched. The
      four live rule anchors are unchanged.
- [x] Every cross-reference to a step number checked: the only one, "step 10" in
      coding-python-performance-review, still names the differential.
- [x] RED by text check of the pre-edit file: `clear_refs`, `background jobs` and `chain` occur
      0 times. Text check chosen because the lessons are in this machine's memory store.
- [x] Step 13 executed before the probe: a child allocating 64 and 128 MiB after a 256 MiB earlier
      peak, interleaved 64/128/64/128, read 64.0/128.0/64.0/128.0 MiB of VmHWM growth after the
      `clear_refs` reset; without the reset the earlier peak would hide all of it.
- [x] GREEN quote-back, opus and haiku, 3 questions on this skill: both tiers quoted the new text
      and answered correctly.
- [x] Gaps from GREEN, closed: when `VmRSS` is read and how many runs per size (opus) - now "read
      just after the reset" and "three runs each as in step 4". Re-probe on haiku: quoted and
      answered correctly, no new gap.
- [x] Width and fence check over the added lines: no output. ASCII only; no private names.
