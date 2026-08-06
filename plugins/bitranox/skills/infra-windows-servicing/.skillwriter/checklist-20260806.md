# skill-writer checklist - infra-windows-servicing (2026-08-06, new skill)

- [x] Change: new skill. Scope is the FALSE SIGNALS in Windows servicing, not the procedure -
      RED showed the procedure is already known.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Type: reference/technique. Test approach: application scenarios, sonnet-pinned, each
      required to end with a "Skill gaps" section.

## RED - baseline without the skill

- [x] S1 "cumulative update fails and rolls back, other fleet machines took it fine":
      FAILED. Ranked component-store corruption as most likely and explicitly dismissed
      headroom - "more consistent with corruption than a marginal space shortfall". The
      measured answer on the motivating fleet was headroom on 15 of 17 machines.
- [x] S2 "rd /s /q refuses one file": PASSED, twice. First run's scenario gave away the
      elimination by stating takeown+icacls had already succeeded; the realistic rerun
      withholding that ALSO passed, producing takeown -> icacls -> attrib -R -S -H /S /D ->
      delete in the correct order, plus robocopy /MIR as a faster bulk form. Weakness, not a
      failure: it ranked ACLs as the cause and the attribute as an afterthought ("sometimes
      carry the System bit").
- [x] S3 "log flat 40 min, last line is the DISM session-end marker": PASSED. Refused to kill,
      checked process liveness, CPU/IO delta and mtimes inside the mount. Its own gaps list
      named the real trap: it could not tell whether that marker ended the whole job or one
      sub-invocation.
- [x] CONTAMINATION, declared: S1 ran before neutral framing was added and quoted material that
      exists only in this machine's always-loaded memory index, which every agent in this tree
      inherits (route 2 - injection keyed to the prompt, not the directory). Per
      testing-skills-with-subagents.md that voids a PASS as evidence; S1 FAILED, so it is used
      only for the failure it exhibited. S2 and S3 ran with explicit neutral framing.

## GREEN - with the skill

- [x] S1 re-run with the skill: PASSED and inverted. "Most likely single cause: insufficient
      free disk space on the system volume ("disk headroom"), not component-store corruption."
      Quoted the governing lines back.
- [x] Gaps reported by GREEN, all three closed in the text:
      (1) no diagnostic ORDER for this symptom - it had to place ScanHealth itself "to avoid
      the exact trap the skill names in its own top table row"; (2) no error code for the
      update-fails path, only for RestoreHealth/setup/Mount-Wim - it guessed 0x80070070;
      (3) "a real installed peer beats an ISO" stated as a preference with no /Source: form.
- [x] Gaps DECLINED with reason: "no command to measure the floor" - closed anyway as part of
      the order block. "Run the repair on ONE machine first is inapplicable to a single
      machine" - reworded to scope it to a fleet.

## RED -> GREEN diff, both directions

- [x] Gained: headroom ranked first; ScanHealth demoted to a ruling-out step; a decisive
      confirm-by-fixing path.
- [x] LOST from baseline, accounted for: the failing-disk branch (Get-PhysicalDisk, chkdsk),
      the AV/EDR branch, and Get-HotFix verification. All three were ranked last by the
      baseline itself for this symptom, and the skill's purpose is to correct the ranking that
      put corruption first. Judged an acceptable narrowing, not a regression - recorded here
      rather than silently traded.

## Verification

- [x] Quote-back on 7 contested questions: all 7 returned verbatim quotes, no NONE.
- [x] One weak result acted on: the SYSTEM-vs-admin answer quoted "The fix is sideways", which
      implies the action without stating it. Rewritten to name the command explicitly.
- [x] Frontmatter parses; name 23 chars; description 408 chars, triggers-only, no workflow
      summary.
- [x] Naming: top-level prefix `infra` is a key in skill-taxonomy.json. `compuse` was rejected
      per the tie-break ("compuse = running-commands mechanics"); this is a domain procedure.
- [x] Security scan: no addresses, MACs, hostnames, private paths, fleet identifiers or
      credentials. Verified by grep, including after the refactor edits added a UNC example
      (\\PEER\C$ - a placeholder, not a real host).
- [x] ASCII only; no bare package-local doc references.
- [x] Ships no scripts, so no tests/ directory is required.
