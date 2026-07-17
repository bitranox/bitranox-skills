# skill-writer checklist - coding-python-performance-review (2026-07-17, test gate can now fail; bootstrap resolves; cache evidence wired; 4f artifact joins its siblings)

Change: Four defects, one a live bug: `TEST_EXIT=$?` after `| tee` reads TEE's status, so the Step 7 gate wrote
SUCCESS over a failing suite - the repo's own gated-rc-from-log trap, in a shipped skill. `SKILL_DIR` was
used at line 132 to launch setup_env.py but only assigned at line 145 from the session.json that script
writes, so it expanded to `/setup_env.py`. profile_with_cache_template.py - the ONLY script computing hit
rate, encoding exactly the >20%/>5% thresholds - appeared in no workflow step, making 'NEVER cache without
evidence' unexecutable. 4f wrote memory_candidates.txt to the tmpdir root while 4a-4e wrote to cache/.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read lines 453-458: `$?` after a pipe is tee's status (tee ~always succeeds) so the gate could
      never fail; grep proved profile_with_cache_template.py occurs only in the reference table (line
      60) and in no step; grep proved 4f alone wrote outside cache/
- [x] GREEN: PIPESTATUS[0] in both branches with a WHY comment; SKILL_DIR set before the bootstrap with the
      reason it cannot come from session.json; the cache experiment wired into the accept path with a
      REJECT branch and the verdict as deliverable; 4f writes to cache/
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
