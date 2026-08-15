# meta-dream-crosstree - promotion-gate verification step

Change: step 4 gains a VERIFY instruction for a `promote` verdict. The corroboration counter keys on
the raw project STRING, so a project spelled differently from an earlier run becomes a second key and
one project is counted as two distinct corroborators.

## RED

The behavioural arm cannot fail on this machine, and that was measured rather than assumed:

- [x] `redcheck.py --corpus-cascade` over the session's always-loaded context reports
      **INHERITED COVERAGE - STRONG**: `reference-the-promotion-counter-keys-on-the-project-string-so-a-renamed-key-fakes-corroboration.md`
      already states the lesson (10 shared terms, 32%), so a dispatched agent answers from the
      cascade, not from the scenario.
- [x] Route taken, per the skill's two options: **a text check of the artifact**, which inherited
      context cannot fake. The behavioural arm was NOT escalated until something failed.
- [x] RED evidence, pre-edit grep of `SKILL.md`: `RAW PROJECT STRING` ABSENT,
      `promotion-candidates.json` ABSENT, `no validation that it names a real level` ABSENT,
      `SECOND key for the SAME project` ABSENT.
- [x] Control on the same run: `saw-promotable` PRESENT - the checker can find text that is there,
      so the four ABSENT results are measurements, not a broken pattern.

## GREEN

- [x] Post-edit, all four terms PRESENT, matched on whitespace-normalised text (the line-based grep
      reported one false ABSENT purely because the phrase wraps across a line).
- [x] Negative control on the same run: `quantum entanglement` ABSENT.
- [x] The instruction is actionable, not a warning: it names the file to open
      (`~/.claude/self-improve-audit/promotion-candidates.json`), what to compare (the recorded
      project keys), and the default when provenance cannot be established (`hold`).

## Evidence the rule is needed

Five slugs returned `promote` on counts of 2 that were one project counted twice, because the
sightings were recorded under bare project names while earlier runs had keyed the same projects
differently. None was promoted. The gate is the only thing between a single-project fact and the
always-loaded index of every session under the tree.

## Quality checks

- [x] Frontmatter `description` UNCHANGED - no `build_skill_triggers.py` rebuild required (verified
      by diffing the `description:` line).
- [x] No session narrative or private provenance in the skill text: the added paragraph states the
      mechanism and the check, names no operator instruction, no tool-reach order, no scratch path.
- [x] No machine-specific addresses, hostnames or home paths added.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over the added lines returns NO matches. The one path the text does name,
      `~/.claude/self-improve-audit/promotion-candidates.json`, is tilde-relative - the store
      location every install shares, not a path off this machine.
- [x] Security scan of the diff: no secrets, credentials, tokens, private hostnames or IPs.
- [x] ASCII only.
- [x] Body remains a numbered-step procedure; no flowchart added (the decision is not branching).

## Skill gaps

- Declined: making `saw-promotable` itself resolve the project to a level path so the key cannot
  drift. That is a code change to `dream_state.py`, not a skill change, and it belongs in its own
  commit with its own tests. The skill now tells the reader to verify, which is what protects the
  gate today.
