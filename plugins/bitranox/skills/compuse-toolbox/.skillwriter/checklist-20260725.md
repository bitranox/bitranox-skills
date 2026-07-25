# skill-writer checklist - compuse-toolbox (2026-07-25)

Change: NEW reference skill (5.99.0). Promotes the generic subset of the local personal toolbox
(procsig, git_state, conflict_scan, ci_triage, jsonl_grep, transcript_tail) to the marketplace,
selected by transcript-frequency + recurring-error-ledger analysis (heavy real use; no host/fleet
coupling). Host-coupled jigs (sshf, guestip, ovmlog) deliberately stay local.

- [x] Skill type: reference (tool index) - test approach is script tests + routing-table accuracy
- [x] Name: `compuse-toolbox` - `compuse` is an existing taxonomy category (no new category/domains change)
- [x] Frontmatter: name + description only; description is trigger-first ("Use when about to hand-roll...")
- [x] Description states triggers/symptoms, no workflow summary; third person
- [x] Body lean: routing table + why-a-jig-over-a-one-liner + enhance rule; per-tool args deferred to `--help`
- [x] Receipt held this session (skill_receipt.py start meta-skill-writer)
- [x] Scripts ship with tests: 6 tools + 6 test files + conftest; `pytest tests/` = 33 passed
- [x] Scripts import-safe (core fn + argparse under `if __name__ == "__main__"`) - unit-tested
- [x] Public scrub: procsig docstring genericized (no openvmm/vmid/ledger refs); scan clean bar `cargo` (generic Rust example)
- [x] Security scan: no secrets, private hosts/IPs, internal paths, or PII in the diff; no shell=True/eval/exec
- [x] Cross-platform: pure Python + uv (PEP 723); no bash logic, no host assumptions
- [x] Routing table accuracy: every listed tool exists in scripts/ and its purpose matches its docstring
- [x] Discoverability probe: pending next marketplace update + reload (queued; not blocking the local commit)
