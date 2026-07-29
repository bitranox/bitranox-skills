# skill-writer checklist - process-test-design (2026-07-29, language-general)

Change: the skill's principles were already language-neutral, but its mechanics were Python-only -
the whole "Run in a clean, project-correct environment" section was venv/uv, the time-and-randomness
rule named only Python functions, and there was no per-ecosystem guidance at all. Added a
"Per-language mechanics" table (Python, TypeScript/JS, Go, Rust, Bash: injection seam, self-mock
tell, real dependency, shuffle flag), a tier-marking rule, a stopping rule for failure-mode
coverage, a resolution of the patch-a-global ambiguity, a language-general lockfile/toolchain rule
with the Python trap kept as a specific, and a widened description. Shipped in plugin 5.102.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED was a real application test, not an inspection: a subagent was given the unedited skill and
      a TypeScript/vitest project (private-method `vi.spyOn`, no e2e, filler tests) and asked for
      concrete runnable fixes plus an explicit "Skill gaps" section. The prompt did not hint that
      the skill was Python-flavoured.
- [x] RED produced five named gaps, and they are the edit's specification:
      (1) the clean-environment section is 100% Python/uv with no JS equivalent - the agent invented
      a lockfile finding "by analogy" and said it could not tell if that matched the author's intent;
      (2) no tier convention outside pytest/bmk, so it invented its own e2e layout;
      (3) a genuine ambiguity - the skill lists "the network" as a patchable edge while also
      demanding a real HTTP proof, and never says which wins when you own the caller;
      (4) no stopping rule for how many failure modes to cover, so it left a known gap unfixed;
      (5) "inject time and randomness" names only Python symbols.
- [x] Two of those (3 and 4) are language-NEUTRAL content gaps, not translation gaps, and are fixed
      as such: the patch-a-global rule now turns on whether you own the caller, and the stopping rule
      is one case per branch the code distinguishes, with a worked HTTP-wrapper example.
- [x] The Python material was generalised, not deleted: the lockfile/pinned-toolchain rule is stated
      for any language with per-ecosystem commands, and the venv trap is kept beneath it as "Python
      specifics, where the trap is most common" - the existing detail keeps its value.
- [x] Languages chosen from what this marketplace and its consumers actually ship (Python, Bash,
      Rust skills exist here; the quality rubric scores TypeScript and JavaScript), plus Go as the
      common interface-injection case. A map-by-role instruction covers anything unlisted.
- [x] Scope: shared/general. The one per-repo item (bmk `make test` vs `make testintegration`) was
      already labelled per-repo and stays in Cross-references.
- [x] Security scan: prose and one table, ASCII only, no secrets, hosts, private paths or PII.
- [x] CSO description: rewritten to trigger outside Python - "in ANY language", plus spy/stub and
      pytest/vitest/jest/go test/cargo test/bats keywords. Still trigger-first, still no workflow
      summary. `build_skill_triggers.py` and `build_skill_docs.py` regenerated for the new text.
- [x] Token budget: reference-leaning skill, 2081 words; the additions are one table plus four short
      rules, and the generalisation replaced Python-only prose rather than stacking onto it.
- [x] `repo-gate.py --ci` run with CI's full dependency set: all checks passed.
- [x] GREEN verified on the same TypeScript scenario: the five RED gaps are closed, and the agent
      attributed the fixes to the skill rather than to its own improvisation - the TS row drove the
      injection fix "no guessing needed", the prune list named both dead tests, the adversarial table
      supplied three missing branches, and the clean-environment rule produced the lockfile finding
      that RED could only reach by analogy.
- [x] REFACTOR round run, because GREEN surfaced three NEW ambiguities - and two of them were
      introduced by this very edit, so shipping without a second round would have traded five gaps
      for three:
      (1) the mechanics table put an in-process `node:http` server under "e2e tier" while the
      determinism rule demands an offline default run, leaving tier placement undecidable;
      (2) the new stopping rule contradicted the adversarial-input table for an axis with no
      matching branch;
      (3) no rule for a behaviour that is documented but never wired up, so the agent had to invent
      whether to commit a red test.
      Fixed respectively by: tier is decided by the DEPENDENCY (external/shared/slow), not by
      realism, so an ephemeral loopback server stays in the default run; the branch rule explicitly
      governs the axis table, with an absent bound reported as a CODE finding instead; and a
      documented-but-unwired feature is a FINDING, never a committed red or skipped test.
- [x] REFACTOR verified by re-asking the four contested questions against the edited skill: all four
      answered with a direct quote of the governing text, and the agent reported "None" under where
      it had to guess.
