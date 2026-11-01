# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` review fixes)

Section `## One large file across proxies` rewritten to match the code after the review fixes:
what bans, evicts or rotates; an origin change stopping the run with exit 2; redirects; the
probe vote; the URL check; the attempt budget covering headers. Description unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote or
      NONE, `bitranox:baseline-probe` on opus and haiku (2 tiers x 3 rounds = 6 cells).
- [x] RED (section text at HEAD, pasted): both tiers answered Q1 "a 404 bans the proxy", Q2 "every
      proxy is banned" with the exit code guessed, Q4 (302 release asset) NONE, Q5 (one ranged
      and two whole-file views) "a tie, exit 1", Q6 (no scheme) a guess with proxy contact NONE.
      Opus also named the old vote bullet self-contradictory: with no two proxies agreeing, every
      view has one vote, so "the view with the most votes wins" cannot happen.
- [x] Each new sentence checked against `chunked_fetch.py`: `_THROTTLED` and `>= 500` rotate;
      `_BAN = {"dead"}` (ConnectError, ConnectTimeout, a ProxyError whose `connect_status` is
      None); `_SUSPECT` evicts via `pool.evict` and `_Witnesses.report` stops at two distinct
      proxies; `MAX_REDIRECTS = 8` and TooManyRedirects is a suspect answer in `attempt`;
      `probe(..., attempts=max_attempts)`; `check_url` runs before `probe`. A stalled proxy is a
      `cut` (TransportError), so the first draft's "no HTTP answer bans" was corrected to the
      three dead cases.
- [x] GREEN round 1 (new section, pasted): 8 of 8 by quote on both tiers, including the control
      Q8 (connects, then silent: rotated, not banned).
- [x] Gaps closed: the attempt budget now says headers are included; "dropped for the rest of
      this run"; what a rerun does after an origin stop (resumes against the probed file, refuses
      the manifest against a replaced one); a chain past 8 hops is an odd answer; the bad-URL
      example names `ftp://...` beside `example.com/big.iso`.
- [x] The rerun sentence executed: `test_a_rerun_after_an_origin_stop_resumes_once_the_url_serves_
      the_file_again` and `test_a_rerun_after_an_identity_stop_refuses_the_old_manifest` pass.
- [x] Gaps declined: a rerun of a whole-file download (the "No Range support" bullet already says
      "with no resume"); an over-long chain during the probe (`probe` records it as a failure and
      casts no vote, and "Only a dead proxy is banned during the probe" covers the ban side);
      whether a zero-byte cut spends an attempt (`run_chunk` counts every attempt, `tries += 1`,
      and "A chunk gives up after `--max-attempts-per-chunk`" states the budget); whether a
      rotated proxy returns in the same run (the pool's flaky eviction, rule 6, owns that).
- [x] Final re-probe of the touched questions on the final text: 6 of 6 by quote on both tiers;
      the only new item (ftp not named) was closed above.
- [x] Added lines under 100 columns; file ASCII-only; no code fence added; history finder clean;
      no address, MAC, hostname or machine path added; present tense.
