# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` third review fixes)

Section `## One large file across proxies`, the `fetch` exit codes and the module docstrings
rewritten to match the code after the third review fixes: no combination of proxy answers makes
exit 2; odd answers evict for the run only and exit 1 names them, grouped by distinct proxy; a
changed file shows on the rerun as a refused manifest (exit 2); only a failed connect bans a proxy
to `bad.txt`. Description unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote or
      NONE, `bitranox:baseline-probe` on opus and haiku.
- [x] RED (section text at HEAD, pasted), both tiers: four agreeing liars beside two honest
      proxies, a URL answering 404 through every proxy, an ETag change after the probe and a
      probe that settled nothing on a shared error all answered "exit 2"; a CONNECT refused with
      302 answered "banned"; opus also banned a proxy whose tunnel opened and whose origin
      handshake then stalled.
- [x] Each new sentence checked against `chunked_fetch.py`: `failure_outcome` returns `dead` only
      for a ConnectError or ConnectTimeout while `Heard.answered` is false, `refused` for any
      ProxyError, `certificate` for an SSLCertVerificationError found through `__context__`, and
      `cut` for the rest; `_DeadlineStream.read` sets `Heard.answered` when data comes back;
      `_probe_views` bans only a `dead` outcome and collects every other answer;
      `describe_answers` groups by distinct proxy, most first; the chunk wait uses
      `cf.FIRST_EXCEPTION` with a timeout, and a failing worker sets the stop event; a changed
      file on the rerun raises `ManifestMismatch` (exit 2).
- [x] GREEN (new section, pasted): 7 of 7 by quote on both tiers. The answer that changed: four
      agreeing liars beside two honest proxies complete the file, exit 0.
- [x] Gaps closed: the 15-second connect rule; the reply is judged before any byte is written;
      the three conditions that end a run (file complete, no proxy left, attempts spent); exit 1
      names the answers when there were any, and a 403, 407, 429, 5xx or refused CONNECT is
      never named; "gave no answer" replaced by "only a failed connect bans", since a proxy that
      closes without a byte is a cut.
- [x] Gaps declined: "fails" undefined (a refused, failed or over-long TCP connect is stated);
      the 15 seconds are not configurable (the fixed `min(timeout, 15)` limit, `fetch --help`);
      the probe budget; rotation semantics (the pool's flaky eviction owns them); attempts spent
      on liars; identity is defined in the vote bullet; a 302 CONNECT as redirect or refusal (the
      answer is the same); `bad.txt` persistence (stated in the earlier rules).
- [x] Final re-probe on the final text, both tiers: 7 of 7 by quote; the reworded ban bullet
      re-probed alone: 5 of 5 by quote, no contradiction with the other bullets.
- [x] Added lines under 100 columns; file ASCII-only; no code fence added; history finder clean;
      no address, MAC, hostname or machine path added; present tense.
