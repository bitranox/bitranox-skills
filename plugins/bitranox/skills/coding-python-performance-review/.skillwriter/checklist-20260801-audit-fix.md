# skill-writer checklist - coding-python-performance-review (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled. Ships with plugin 5.126.0.

- [x] WRONG, the most serious here: `profile_with_cache_template.py` monkey-patched the target
      function in THIS process and then ran the suite via `subprocess.run`, which gets a fresh
      interpreter that never sees the patch. `cache_info()` therefore reported 0 hits and 0 misses,
      the hit rate computed as 0, and `recommend()` returned REJECT no matter how good the cache
      was - a decision tool that always answered the same way. Both runs now call `pytest.main()`
      in-process.
- [x] Two regression tests added and PROVEN RED against the pre-fix template in a throwaway
      worktree: one drives the real `profile_with_cache` through a fake suite and requires hits to
      appear (1 hit, 1 miss, 50%), one pins that the argv carries no interpreter prefix.
- [x] WRONG: the skill promised `uv run setup_env.py` "fetches an isolated 3.13+ interpreter", but
      the file carried no PEP 723 block, and uv reads inline metadata only from the file it is
      handed. Added `requires-python = ">=3.13"` so the claim is true rather than deleting it.
- [x] WRONG: the reference table described `validate_perf_claims.py` as validating claims. Its own
      docstring and output say it EXTRACTS them for the reader to validate against a profiled run.
      Row corrected.
- [x] WRONG: prose required a hit rate ">20%" while the code rejects only below 20 and the triage
      rule elsewhere calls "<20%" ineffective. Two of three agreed, so the prose moved to ">=20%".
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file before acting; every executable claim re-run rather
      than taken from the report.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
