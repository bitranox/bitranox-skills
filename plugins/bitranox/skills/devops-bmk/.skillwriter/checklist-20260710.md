# skill-writer checklist - devops-bmk (2026-07-10)

- [x] Change: documented why local `make test` can diverge from CI - added a "Make `make test` match CI" note to section 6 (the `[tool.scripts.test].exclude-markers` key, default `"integration"`; set `"local_only"` to mirror CI; bmk >= 3.1.7 provisions its tool venv with the project `[dev]` extra) and two Troubleshooting rows. Reference-tier skill; scope is every bmk project whose host/dev tests use the `local_only` marker.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED baseline: sonnet subagent, current skill + scenario (make test runs local_only tests and fails a [dev]-only import while CI passes) answered "SKILL DOES NOT COVER THIS" for the exclude-markers key and the [dev]-extra resync - gap confirmed.
- [x] GREEN verify: sonnet subagent, updated skill + same scenario named the exact key + default, the local_only fix, and the bmk >= 3.1.7 dev-extra fix - no "SKILL DOES NOT COVER THIS".
- [x] CSO: frontmatter description unchanged (still trigger-first "Use when ..."), so no trigger-map rebuild needed; added keywords (exclude-markers, local_only, [dev] extra, tool venv) live in the body.
- [x] Mirror: bmk repo twin (public/apps/utils/bmk/skills/devops-bmk/SKILL.md) synced byte-identical; both plugin.json bumped (marketplace 5.55.0 -> 5.55.1, bmk repo 1.0.1 -> 1.0.2).
- [x] Security scan: prose/doc edit only; example placeholders (`<TOKEN>`, `<ORG>`), no secrets, hostnames, IPs, or PII.

## Correction (bump 5.55.1 -> 5.55.2): fix the make test / local_only / integration model

The change above framed the local-vs-CI difference as a problem and advised `exclude-markers =
"local_only"` to "match CI". That mental model is WRONG (bmk's default `exclude-markers = integration`
is intentional: `make test` is meant to run `local_only` locally). This corrects it.

- [x] Change: replaced the "match CI" note with the correct model - `make test` runs unit + `local_only`, skips `integration` by default; `local_only` = local-resource tests run locally and excluded from CI; `integration` = the long lane via `make testintegration`; raise `exclude-markers` only to skip host-MUTATING tests (tag `mutating`, set `exclude-markers = "mutating"`). Added a marker-taxonomy table (`os_*` / `local_only` / `integration`) and rewrote the troubleshooting rows.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: sonnet subagent, the shipped "match CI" note -> advised "yes, set exclude-markers=local_only", excluding fast/safe local tests, not distinguishing safe from mutating - wrong advice confirmed.
- [x] GREEN: sonnet subagent, corrected note -> "No, do not match CI; running local_only in make test is by design; tag mutating + set exclude-markers=mutating for host-mutating tests" - correct.
- [x] Mirror: bmk repo twin synced byte-identical; plugin.json bumped (marketplace 5.55.1 -> 5.55.2, bmk repo 1.0.2 -> 1.0.3).
- [x] Security scan: prose/doc edit only, no secrets, hostnames, IPs, or PII.
