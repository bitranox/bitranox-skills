# skill-writer checklist - process-review-enhance-code-quality (2026-11-03, cost rows read, not measured)

- [x] Change: one paragraph after the aspect checklist's "Report per sweep" paragraph. It says
      the cost rows (Algorithmic cost, the memory growth under Concurrency, Unbounded input) are
      walked by reading, that the sweep times, profiles and benchmarks nothing, so a finished
      loop is not a performance review; it points at `bitranox:coding-python-performance-review`
      for the measured part on a Python project, as a pass of its own, and requires the final
      report to say performance was read, not measured, when that pass did not run.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the editing agent loaded
      bitranox:meta-skill-writer through the Skill tool before the edit.
- [x] Skill type: process skill, scope statement plus a pointer; test approach: quote-back
      retrieval probe on an excerpt, both tiers.
- [x] Inherited context: `redcheck --corpus-cascade` named one tree-top index file on 4 ordinary
      shared terms (asks, batch, performance, timing); that file does not state the claim, so the
      hit is a false positive. Text check of the pre-edit file (`git show HEAD:<path>`): no
      mention of the performance skill, profiling or timing in the sweep.
- [x] RED (pre-edit excerpt: workflow, severity line, aspect checklist and the paragraphs after
      it; bitranox:baseline-probe, text only, Skill gaps requested), haiku and opus: "Does the
      text say the sweep times or profiles nothing?" NONE on both tiers; "Which skill does the
      text point to for measuring performance?" NONE on both tiers. Both inferred reading-only
      coverage without a governing line.
- [x] GREEN (same excerpt with the new paragraph), haiku and opus: both quoted "it times,
      profiles and benchmarks nothing", the pointer sentence and "When it did not run, the final
      report says that performance was read, not measured."
- [x] GREEN diffed against RED both ways: every RED answer (reading-only coverage, the MEDIUM
      line, the cost rows) is still given in GREEN; nothing the baseline answered was lost.
- [x] Gaps closed: (1) GREEN on haiku found that "or as a performance subagent beside the
      sweep's reviewers" leaves open whether that subagent's findings count toward the exit
      gate; the clause is removed and the pass is "a pass of its own". (2) GREEN on opus found
      the memory growth and Unbounded input rows equally read-only; the paragraph now names all
      three cost rows.
- [x] Gaps declined: the exit gate's treatment of slow-but-correct performance findings
      (pre-existing gate rule, not about this scope statement, never ruled on by the user); no
      named owner for MEASURING peak memory (the performance skill flags unbounded memory by
      reading too, coding-python-performance-review SKILL.md:29-35 and its AST finder at line 62,
      so pointing at it for peak-memory measurement would be false; adding a measurement step is
      new behaviour nobody asked for); non-Python projects (no other-language performance skill
      ships; grep of skills/*/SKILL.md for "performance"); exact report wording and placement
      (one plain statement in the final report is what the sentence says; both tiers read it so);
      the eleven rows elided in the excerpt (the full file holds no measurement claim in them,
      text check above).
- [x] Re-probe on the final text, haiku and opus, with a memory question added: both quoted the
      new paragraph for Q1, gave NONE for "was memory growth measured" with the read-only line
      as the reason, quoted "as a pass of its own" and the report sentence. No new undecided gap.
- [x] Pass also run on the weakest tier: tiers haiku and opus; cells: RED 2, GREEN 2, final 2.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion (Error contract) reads unchanged and binds to nothing in the new text.
- [x] Cases decided beyond the request: none. The subagent placement was removed rather than
      decided.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; ASCII only.
