# skill-writer checklist - devops-bmk (2026-07-10)

- [x] Change: documented why local `make test` can diverge from CI - added a "Make `make test` match CI" note to section 6 (the `[tool.scripts.test].exclude-markers` key, default `"integration"`; set `"local_only"` to mirror CI; bmk >= 3.1.7 provisions its tool venv with the project `[dev]` extra) and two Troubleshooting rows. Reference-tier skill; scope is every bmk project whose host/dev tests use the `local_only` marker.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED baseline: sonnet subagent, current skill + scenario (make test runs local_only tests and fails a [dev]-only import while CI passes) answered "SKILL DOES NOT COVER THIS" for the exclude-markers key and the [dev]-extra resync - gap confirmed.
- [x] GREEN verify: sonnet subagent, updated skill + same scenario named the exact key + default, the local_only fix, and the bmk >= 3.1.7 dev-extra fix - no "SKILL DOES NOT COVER THIS".
- [x] CSO: frontmatter description unchanged (still trigger-first "Use when ..."), so no trigger-map rebuild needed; added keywords (exclude-markers, local_only, [dev] extra, tool venv) live in the body.
- [x] Mirror: bmk repo twin (public/apps/utils/bmk/skills/devops-bmk/SKILL.md) synced byte-identical; both plugin.json bumped (marketplace 5.55.0 -> 5.55.1, bmk repo 1.0.1 -> 1.0.2).
- [x] Security scan: prose/doc edit only; example placeholders (`<TOKEN>`, `<ORG>`), no secrets, hostnames, IPs, or PII.
