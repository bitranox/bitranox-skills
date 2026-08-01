# skill-writer checklist - meta-skill-audit (2026-08-01, new skill)

New skill: auditing a catalogue of already-shipped skills for defects, as distinct from authoring
or editing one. Ships `scripts/audit_skills.py` (clean-room sweep, one reviewer per skill) with
tests. Ships with plugin 5.125.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test approach is an application scenario - can a reader turn it into
      an executable audit?
- [x] Prior art surveyed within this marketplace first: `meta-skill-writer` owns authoring and
      RED/GREEN, and its "Watch for baseline contamination" section owns the isolation mechanics.
      This skill cross-references both rather than restating them, and starts where authoring ends.
- [x] RED ran in a clean room (temp dir outside the tree, recall walled) on a weak, literal model,
      asking how to audit a ~66-skill catalogue with subagents. It FAILED on the load-bearing
      point: "All agents run against the full plugin skills directory (e.g.,
      `/home/srvadmin/.claude/plugins/cache/bitranox-skills/bitranox/5.124.0/skills/`)" - the live
      install on the same machine, with no isolation and no mention of the recall hook, so every
      reviewer would be fed the memory index it is supposed to be measured against.
- [x] Reported rather than claimed: the RED did NOT fail on the install-unit question. It said to
      check "the skill dir OR plugin root", which is right. That rule is in the skill on the
      strength of a MEASURED defect instead - the first smoke run of the harness judged
      reachability against one skill directory and 5 of its 6 findings were siblings and plugin
      hooks reported as dangling. A measured false-positive rate is stronger evidence than a
      baseline opinion, and it is labelled as such.
- [x] The RED's own gaps list fed the skill: it flagged that regex-extracted cross-references
      produce false positives, and that an "install-local `--help`" claim is unverifiable if the
      tool is absent. Both are why the triage table pairs every finding class with its usual false
      positive rather than listing classes alone.
- [x] Script ships with tests: 14 cases in `tests/`, covering the prompt contract (install unit,
      verbatim quote, gaps section), skill enumeration, room preparation including artifact
      exclusion and the reuse path, finding counts, and an end-to-end audit through an injected
      reviewer. Two pin the properties that matter most: every reviewer runs with the ROOM as cwd,
      and a reviewer timeout is recorded rather than silently counted clean.
- [x] The reviewer is injected at a `runner` seam, so the tests drive the real module with a
      substitute reviewer instead of patching internals.
- [x] Script is import-safe (all work behind `main()`), pure standard library, LF, and launched via
      `hooks/run-python.sh` per the cross-platform rules.
- [x] Cross-references use skill names with a REQUIRED marker; the bundled script is named with its
      home (`skills/meta-skill-audit/`) and its launch shim at point of use.
- [x] Description is triggers-only ("Use when auditing or reviewing a whole catalogue..."), names
      the distinction from authoring, and carries the phrases a user would actually type.
- [x] Derived artifacts regenerated: `skill_triggers.json` (67 skills), `docs/skills.md`, and the
      README count 66 -> 67.
- [x] No session narrative or private provenance in the skill text; no addresses, MACs, hostnames
      or machine paths added.
- [x] Honest limitation stated IN the skill rather than hidden: one reviewer per skill per run is a
      sample, so a skill that reports clean once is unmeasured rather than verified clean.

## Amendment, same session: deterministic checks first

- [x] The sweep's own results changed the skill. A one-second `ast.parse` over every shipped `.py`
      in the catalogue found the same broken example a reviewer had spent minutes reaching, and
      proved the other 65 skills clean of that whole defect class at the same time. The skill now
      opens with the deterministic pass and reserves reviewers for what needs judgement or a live
      tool.
- [x] Verified before claiming: the sweep script reported `broken shipped .py files: 0` after the
      fix, and had reported the `border_title.py` SyntaxError before it.
- [x] Second amendment, also from the sweep's own behaviour: a reviewer pip-installed a package
      into the ambient environment at 02:41 while verifying a skill's claims, which flipped that
      skill's tests from skipping to running and turned a previously green gate red. The clean room
      isolates CONTEXT, not the filesystem. Recorded in Common Mistakes with the instruction to
      re-run the gate after a sweep rather than trusting a pre-sweep result.
- [x] Third amendment: a gate run that OVERLAPPED the sweep reported two failures that neither the
      isolated CI dependency set nor the ambient interpreter could reproduce once the concurrent
      installs settled. Recorded as its own mistake - gate before or after a sweep, never during,
      and re-run rather than debugging a result from the overlap.
