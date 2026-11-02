# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` second review fixes)

Section `## One large file across proxies` and the `fetch` exit codes rewritten to match the
code after the second review fixes: a refused CONNECT rotates and never counts toward a stop; two
agreeing liars stop nothing while another proxy keeps receiving the file; an untrusted origin
certificate is an odd answer, never a ban; a budget spent during connect or handshake is a cut; a
probe that settled nothing exits 2 on an error two proxies share; the timeout for a rangeless
origin. Description unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote or
      NONE, `bitranox:baseline-probe` on opus and haiku.
- [x] RED (section text at HEAD, pasted), both tiers: two injecting proxies among twenty "stop
      the run with exit 2"; a CONNECT refused with 405 NONE; a self-signed origin "bans every
      proxy"; a URL answering 404 through every proxy between exit 1 and 2; a 4 GB rangeless
      file with no documented timeout fix. A budget spent in the TLS handshake: opus named the
      text self-contradictory, haiku answered "cut", where the code at HEAD banned the proxy.
- [x] Each new sentence checked against `chunked_fetch.py`: `_bounded` raises `BudgetSpent` (a
      cut) when the budget, not the operation's own timeout, ends a connect or handshake;
      `connect=min(timeout, 15)` is the per-operation limit; `_refused_connect` gives `refused`
      for a ProxyError with a status and `dead` without; `_connect_failed` gives `certificate`
      for an SSLCertVerificationError in the cause chain; `_probe_error` names a status other
      than a vote, 403, 407, 429 or 5xx; `probe` records no vote and no error for a refused
      CONNECT, so an all-refused probe returns None (exit 1); `_Witnesses.valid` is called once a
      reply passes every check, before `open()`.
- [x] GREEN (new section, pasted): 10 of 10 by quote on both tiers.
- [x] Gaps closed: "never counts toward stopping the run" for a refusal; GiB/MiB units and the
      4096-second figure; the 15-second rule is per operation and names the handshake with the
      origin; "valid reply" defined; "A refused CONNECT is never such an error" in the probe
      bullet; exit 2 says "no usable proxy in the store at the start"; "same answer" defined; a
      budget that runs out during the connect or the handshake is a cut, never a ban; exit 1
      names a refused CONNECT among the answers that settle nothing.
- [x] Gaps declined: two injecting proxies colluding on one planted whole-file view in the probe
      (the probe's vote design, unchanged here); "rotate" undefined (the pool's flaky eviction,
      rule 6, owns it); whether a rotated or banned proxy spends an attempt (`run_chunk` counts
      every attempt and the bullet states the budget); `--workers` in no-Range mode; advice for a
      pool whose every proxy refuses CONNECT (exit 1 says grow the pool); a safety margin above
      size divided by speed; a cut after a valid reply still counts as valid (that is the code:
      the check passed, so the origin answered the probed file).
- [x] Final re-probe of the touched questions on the final text, both tiers: 6 of 6 by quote, then
      the two gaps it found (handshake budget, refused CONNECT in exit 1) closed and re-probed: 3
      of 3 by quote, including the control Q14 (a 16-second connect that fails with budget left:
      banned).
- [x] Added lines under 100 columns; file ASCII-only; no code fence added; history finder clean;
      no address, MAC, hostname or machine path added; present tense.
