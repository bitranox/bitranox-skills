# skill-writer checklist - process-plan-brainstorming (2026-10-29, backlog 960)

Change: a new first-step bullet under "Understanding the idea", "Ask WHETHER before any HOW
question", and a description trigger for a request that reverses an earlier user decision.

- [x] RED (text check of the pre-edit file, `git show HEAD:.../SKILL.md`):
      `grep -ciE 'worth having|revers|earlier'` counted 0. The only related line was the Key
      Principle "YAGNI ruthlessly - Remove unnecessary features from all designs", which prunes a
      design already under way and says nothing about asking whether the feature should exist
      before a scope question; the description named only unsettled new work, so a request to
      undo a decision just made did not match it.
- [x] GREEN (quote-back): "**Ask WHETHER before any HOW question.** State whether the requested
      feature is worth having at all, with a recommendation: what already covers the need (a call
      site, an existing option, the default), what it costs to keep, and YAGNI." and "name that
      decision and its reason, and recommend for or against reversing it before asking anything
      else."
- [x] Description stays trigger-only (no workflow), third person, starts "Use when": measured
      `len()` = 291 (cap 1024).
- [x] The example (a setting to turn off what the user just chose to have no setting for) is
      generic; no project names.
- [x] ASCII only; no address, host or private path added.
- [x] Not a mirrored skill (`repo-gate.py --mirrors` lists no twin for it).
- [x] Derived artifacts (`skill_triggers.json`, `docs/skills.md`) are stale after the description
      change and are regenerated at integration; the two sync tests fail until then.
- [x] Gaps declined: routing of the new trigger is unverified behaviourally (a live routing probe
      on a machine with the skill installed answers from the installed description).
