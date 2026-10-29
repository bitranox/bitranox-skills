# skill-writer checklist - coding-resilience (strict read inside a wait loop)

- [x] Change: SKILL.md Patterns gains "A strict status read stays strict for a DECISION, not inside
      a bounded WAIT" with the two-test recipe; Common mistakes gains a row.
- [x] RED (text check): `grep -niE 'strict|wait loop|poll|transient'` found only the generic retry
      bullet; nothing on a strict read inside a wait.
- [x] The two-test recipe run against a fail-fast and a tolerant wait loop with a scripted fake
      reader: both tests FAIL on the fail-fast loop and pass on the tolerant one
      ("2 failed, 2 passed").
- [x] GREEN quote-back: "a failed read means \"not there yet\": the loop must keep polling through
      it to its deadline, and on timeout name the LAST failure in its error".
- [x] Description: unchanged.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
