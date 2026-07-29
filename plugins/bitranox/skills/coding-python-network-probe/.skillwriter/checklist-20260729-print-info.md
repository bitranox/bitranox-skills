# skill-writer checklist - coding-python-network-probe (2026-07-29, full coverage)

Change: add `print_info` to the quick reference, taking the skill to every command and every
public name. Shipped in plugin 5.101.2.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the skill covered 29 of 30 callables. `print_info` had been left out earlier the same
      day as a deliberate call - a metadata printer behind the `info` command, which is listed.
- [x] Reversed on consistency grounds, not because the omission was harmful. The coverage rule
      shipped in process-review-enhance-code-quality hours earlier says every public name must
      appear; an exception argued for one's own artifact is weaker than a single table row, and a
      rule whose author exempts himself is not a rule.
- [x] GREEN, verified by the same script the rule prescribes, run against the live `--help` output
      and `__all__`: 18/18 commands, 30/30 callables, zero gaps, on both copies.
- [x] Claims half also re-run on this skill: four absence/contract claims, each verified against
      real behaviour, and the load-bearing one (`is_reachable` never raises) is pinned by
      tests/test_integration_loopback.py.
- [x] Copies byte-identical, synced after the ipscout formatter ran.
- [x] Scope: shared/general. Security scan: one table row, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description unchanged; token budget one row.
