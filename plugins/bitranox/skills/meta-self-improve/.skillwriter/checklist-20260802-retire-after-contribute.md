# skill-writer checklist - meta-self-improve (2026-08-02, a contribution ends by retiring the local copy)

Change: the CONTRIBUTE rung of the chore ladder now states that landing a tool upstream is only half
the work, and the local original plus its tests are deleted to finish it - the same two-step shape
the hook-lifting rule above it already spells out. Also removes a duplicated "a shared" and the
reference to a `meta-toolbox` skill that was never shipped.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued this session).
- [x] ROOT CAUSE, not a symptom fix: the rung ended at "landing it in a shared skill... Never
      automatic" and said nothing about the original. The hook rung three bullets earlier already
      says "a TWO-STEP retirement, and half of it is worse than neither" - tools simply never got
      the equivalent sentence, so every contribution left a duplicate behind by default.
- [x] MEASURED before writing, not asserted: eight local tools had shipped twins, and all eight had
      drifted. Compared with docstrings stripped via `ast.dump` to establish the drift was prose,
      not logic, so the rule could say what is actually true (the shipped prose is the better one)
      rather than implying the copies had diverged in behaviour.
- [x] The rule carries the failure it prevents: a nudge or doc keyed on the local path falls SILENT
      when the local copy is deleted. Found by checking callers before deleting, per "confirm no
      crontab, systemd timer or doc still invokes the old name" - `toolbox-nudge.py` guarded on the
      local file and would have gone quiet for the eight tools most worth nudging about.
- [x] Fixed the guard it names rather than only documenting it: `toolbox-nudge.py` now resolves the
      shipped copy when there is no local one, via a path relative to the hook itself - a
      version-pinned path would rot at the next update, and the old cache dir is pruned.
- [x] An existing test asserted the OLD contract (silent when the local tool is absent). Rewritten
      to assert the fallback, with a second test keeping the genuine silence case (present neither
      locally nor shipped) - the assertion was replaced, not deleted.
- [x] Enforcement, not just prose: the local toolbox's own suite gained a test that fails if any
      local tool duplicates a shipped compuse-toolbox one, so the end state is pinned. It no-ops
      where the repo is absent, so it does not break on another machine.
- [x] Escalation ladder honoured - this is the first documented occurrence of the tools variant, so
      it earns a rule now, and the duplication guard is the deterministic backstop.
- [x] No session narrative or private provenance added; no machine paths added to the SKILL.md.
