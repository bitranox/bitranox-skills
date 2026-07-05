# skill-writer checklist - infra-proxmox (2026-07-06, roster review wave 1)

- [x] Change: flattened the `>-` folded-scalar description (added the CLI tool names pvecm/qm/pct/pvesm/pveceph/ha-manager/pvesh/vzdump as keywords); added the ch19-cli-tools.md routing row; deleted the orphaned verbatim duplicate onaction.md. Deferred (maintainer decision): monolith-vs-hub redesign of the 6.4k-word body.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent, scenario picked this skill from a 12-candidate list (wave 6/6)
- [x] Security scan: prose/frontmatter edits, no secrets/paths/PII

# skill-writer checklist - infra-proxmox (2026-07-06, lean-hub restructure)

- [x] Change: body restructured from a 6,474-word monolith to a 1,691-word hub (user decision) per an opus dedupe map verified against the chapter files: kept inline only the gates (auto-detect table, safety table, action-review protocol, response style, cluster-size table, troubleshooting triage) plus the routing tables; near-verbatim command dumps (sections 2-4, 7-18, 22-25) removed - all reachable via existing routing rows.
- [x] Unique content preserved by folding BEFORE deleting: Docker-in-LXC host-ops -> ch11-containers/security-and-os-config.md; node-maintenance runbook -> ch03-host-admin/node-management.md; the config-file path map -> appendix-c-config-files.md (the map's verify-flag caught that appendix-c did NOT already carry it - only datacenter.cfg matched).
- [x] Five routing rows added (migration, cold start, node evacuation, pvesh, Docker-in-LXC); fable routing test 6/6 incl. all new rows and both fold destinations.
- [x] Inbound-reference safety: repo-wide grep found zero section-level links into SKILL.md (name-only references).
- [x] Receipt held; description unchanged (generators in sync); security scan clean.
