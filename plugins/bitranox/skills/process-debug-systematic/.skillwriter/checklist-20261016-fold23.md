# skill-writer checklist - process-debug-systematic (2026-10-16, fold23)

- [x] Change: paragraph "Diff a working peer before calling a fault external." added in "When Process Reveals 'No Root Cause'" (peer diff, VERSION first then config then environment; "nothing changed locally" is not evidence of an external fault; "no error logged" is not "it succeeded").
- [x] Change: Phase 2 step 1 "Find Working Examples" gained a bullet pointing a service or host fault at a comparable working host.
- [x] Change: the Phase 1 multi-layer example's secret check `${IDENTITY:+SET}${IDENTITY:-UNSET}` replaced by `[ -n "$IDENTITY" ] && echo SET || echo UNSET`. Tested: with IDENTITY set the old line printed `IDENTITY: SET<value>` (the `:-` expansion yields the value), the new line prints `IDENTITY: SET`; both print `UNSET` when unset.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the skill had no text for the rule. Verifier gap: "Nothing in the skill tells an agent who suspects an external or environmental fault to ask whether a comparable host works, and then to diff the two hosts, software VERSION first, then config, then environment". Behavioural RED replaced on purpose because the rule is in the always-loaded memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier): diff a working peer -> SKILL.md "Diff a working
      peer before calling a fault external" (No Root Cause section) and the Phase 2 "Find Working
      Examples" bullet. Secret example, both layers run in bash under set -u with IDENTITY set,
      empty and unset: `IDENTITY: SET` / `IDENTITY in environment`, `IDENTITY: UNSET` /
      `IDENTITY in environment`, `IDENTITY: UNSET` / `IDENTITY not in environment`; the value is
      never printed. Layer 2 was `env | grep IDENTITY`, which printed the value; now `grep -q`.
- [x] Gaps closed or declined: layer-2 leak closed; `${IDENTITY-}` added so the check survives
      `set -u`. Pre-existing non-ASCII symbols elsewhere in the file are out of scope.
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
