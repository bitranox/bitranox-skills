# skill-writer checklist - process-review-enhance-code-quality (2026-07-29, sweep until clean)

Change: the review now loops. An outer sweep repeats from Step 2 whenever the previous sweep found
or fixed anything, and stops only on a sweep that walked a twelve-row aspect checklist and changed
nothing. Step 7 renamed from "Re-score" to "Sweep again, and only then re-score"; three rows added
to Common Mistakes. Shipped in plugin 5.101.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, from a user complaint rather than a hypothetical: "I needed to call it 4 times until no
      findings. It should do that itself." Reading the workflow confirms the structural cause -
      "More issues? -> no -> 7. Re-score" loops over THIS pass's issue list and then exits. There
      was never an instruction to analyse again. The sibling skill
      coding-python-enforce-data-architecture-strict has exactly that loop
      ("REPEAT STEPS A->B UNTIL total_violations == 0"); this one did not.
- [x] Both causes addressed, because either alone leaves the bug:
      (1) no outer loop - fixed with the sweep-again rule and the redrawn diagram;
      (2) a sweep that is not systematic - fixed with the aspect checklist, since an unguided
      sweep looks where the last thing led, which is why sweep 1 missed what sweeps 2 and 3 found.
- [x] Evidence written into the skill is measured, not invented: four invocations found 4, 2, 1, 0.
      Sweep 2 found a correctness bug producing silently wrong results under concurrency; sweep 3
      found a quadratic loop worth about eighteen minutes on a wide input. Both were present and
      reachable during sweep 1.
- [x] The fixes-create-findings half is also from observation, and is the more surprising one: a
      gather-to-pool change made results arrive out of order and silently broke zip-by-position
      pairing; a typed facade was re-derived as a bare import in a sibling module, breaking the
      check it existed to fix; a test fixture wrote platform-translated newlines and reddened CI on
      an untouched file. A reviewer who stops after fixing never sees any of these.
- [x] Exit condition is stated as a property, not a count: a sweep that walked every row and
      changed nothing. A bare "no findings" is explicitly called out as indistinguishable from
      having stopped looking, and the skill now requires naming the rows walked.
- [x] Guarded against the opposite failure - endless sweeping - by making the exit concrete and
      reachable, and by keeping the existing rule that a settled accepted item is respected
      silently rather than re-raised each sweep.
- [x] Scope: shared/general - no project-specific content; the checklist rows are language-neutral.
- [x] Security scan: prose and a table, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body and workflow edit, frontmatter untouched).
- [x] Token budget: a process skill that is a checklist by nature; one diagram redrawn, one step
      rewritten, one table and three mistake rows added.
