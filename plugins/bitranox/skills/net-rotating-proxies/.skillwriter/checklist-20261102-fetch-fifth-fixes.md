# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` connect-ban wording)

Two bullets of `## One large file across proxies` reworded, behaviour unchanged: the rotation
sentence now says a proxy that answers an https CONNECT with a non-success status rotates (it
said "any CONNECT the proxy refuses", which reads as a TCP refusal); the ban bullet now says what
a failed connect is ("refused", "fails at once (for example no route to it)", "no reply for more
than 15 seconds while the attempt's budget still has time left"), that a budget running out
during the TCP connect is a cut, and that with a `--chunk-timeout` of 15 s or less a connect that
gets no reply at all only rotates while a refused connect still bans. Description unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote,
      `bitranox:baseline-probe` on opus and haiku, the two bullets pasted.
- [x] RED (the two bullets as committed), `--chunk-timeout 10`, both tiers: Q1 refused connect
      -> banned and Q2 silent drop -> rotated, answered correctly on both tiers; Q3 (wording a
      reader could take to contradict Q1) found, on both tiers, "a proxy that never accepts the
      TCP connect is only rotated, never banned" (a refusal is also "never accepts") and the
      rotation sentence's "any CONNECT the proxy refuses" (one word for a CONNECT reply and a TCP
      refusal). Both also reported "fails" as undefined and the scope of "while the budget still
      has time" as unclear.
- [x] Each claim checked against the code and a measurement: `failure_outcome` returns `dead`
      only for a connect error before anything was heard; the round-3 re-review measured a
      refused port -> dead at 0.0 s, a black-hole address -> cut at a 5 s and 10 s budget and
      -> dead at 15.0 s with a 20 s budget (http and https alike), ENETUNREACH -> dead;
      `_client` sets `connect=min(timeout, 15.0)`.
- [x] GREEN (the reworded bullets), both tiers, four questions (Q4: 30 s budget, silent drop):
      opus 4/4 and haiku 4/4 by quote; neither found a contradiction of Q1. Gaps closed after
      GREEN: "fails" -> "fails at once" (haiku read a silent drop as possibly "fails"); "during
      the connect" -> "during the TCP connect" (opus: "connect" also names the CONNECT request).
- [x] Final re-probe of the final text, both tiers, five questions (adds Q4: 30 s budget, proxy
      accepts TCP and never answers CONNECT -> rotated): results recorded below.
- [x] Declined gaps, each with its reason:
      - default `--chunk-timeout` not stated: covered at SKILL.md line 138 ("`--chunk-timeout
        120` (seconds)"); the probes saw an excerpt only.
      - whether a rotated proxy is picked again: covered by the `--cooldown` and
        `--flaky-fail-ratio` text (SKILL.md lines 53, 65, 107-108).
      - whether a ban counts toward `--max-attempts-per-chunk`: the bullet ends "A chunk gives up
        after `--max-attempts-per-chunk`"; per-attempt accounting is the tool's business, not
        the reader's.
      - a local error (no free ports or descriptors, the host's own network down) read as a
        failed connect: recorded as a known limit of the ban rule (it predates this edit and
        the reword does not change it); out of scope for a wording fix.
      - the OS giving up on a SYN before 15 s: Linux's default SYN retries run far longer than
        15 s, so the 15 s clamp ends the connect first; not worth a sentence.
      - SOCKS proxies: the tool speaks HTTP proxies only; out of scope here.
      - whether 15 s is configurable or strict: an implementation constant; the text gives the
        rule a reader needs (15 s or less never bans a silent connect).
- [x] Width and fence check over the added lines: no line over 100 columns, no open fence.
- [x] No addresses, hosts or paths added; ASCII only; describes current behaviour only.

## Final re-probe (final text)

| Question                                          | opus    | haiku   |
|---------------------------------------------------|---------|---------|
| Q1 timeout 10, refused connect                    | banned  | banned  |
| Q2 timeout 10, silent drop                        | rotated | rotated |
| Q3 timeout 30, silent drop                        | banned  | banned  |
| Q4 timeout 30, accepts TCP, never answers CONNECT | rotated | rotated |
| Q5 contradiction                                  | none    | none    |

Haiku's further gaps, all declined: Q4 "needed inference" (the sentence "A proxy that accepts the
connection and then sends nothing until the budget runs out ... is a cut" is the direct answer);
the 15 s boundary and whether it is configurable (declined above); "fails at once" has no time
bound (it names an error the OS reports, with "no route to it" as the example, not a timeout); a
proxy silent for a while that then accepts (the same accepts-then-sends-nothing sentence covers
it); whether a silent connect counts as "answered" (the text defines an answer as a CONNECT reply
or a byte, which is how haiku read it).

Opus's gap that was real: "fails at once" is narrower than the code. `failure_outcome` bans on any
connect error before the proxy answered, whatever its timing, so a "host unreachable" after 3 s
of a 10 s budget bans. The wording became "ends in any other error before the budget runs out
(for example no route to it, however long that error takes)", "it gets no reply" became "gets no
reply at all" (one subject, the TCP connect), and "(neither accepted nor refused)" became "(no
accept, no refusal, no error)". This error came from my own GREEN-gap fix and passed GREEN on
both tiers: a probe tests that the text is consistent, not that it is true.

## Re-probe v3 (adds Q5: 3 s host-unreachable at a 10 s budget -> banned; Q6: a refused
## reconnect after a redirect, the proxy having answered -> rotated)

Both tiers answered Q1-Q6 correctly. Both flagged the same remaining gap: the closing sentence "A
connect refused or ended by an error before the budget runs out still bans" carried no carve-out
for a proxy that already answered earlier in the attempt, so it reads against "nothing later on
that attempt bans it" (haiku called its own Q6 answer a guess). Fixed: "..., unless the proxy
already answered earlier in that attempt." Matches the code: `heard.answered` gates the ban.

Further gaps from v3, declined: when the 15 s clock starts and the exact 15.0 s boundary (an
implementation constant, declined above); whether any 2xx counts as CONNECT success, and statuses
like 401 or 404 (outside these two bullets; the reply-classification bullet covers them); what a
ban costs in attempts and whether a banned proxy returns (declined above; `bad.txt` is the
store's permanent list, documented with the pool); "any other error" is open-ended (deliberately:
every connect error before an answer bans); DNS for a proxy hostname (pool entries are host:port
from the store, the same rule applies).

## Re-probe v4 (the carve-out sentence): results below.

haiku v4: Q1 banned, Q2 banned, Q3 not banned (decided by the new carve-out, quoted), Q4 rotated,
no contradiction. Its gaps, declined: whether a refused reconnect after an answer rotates (the
excerpt it saw left out the cut bullet; in SKILL.md every failure after an answer is a cut, and
"A cut ... rotates the proxy"); "a silent connect is not a failed connect in the ordinary sense"
(the bullet defines what it means by a failed connect, silence past 15 s included); the budget
equals `--chunk-timeout` (stated in the cut bullet: "`--chunk-timeout` (the budget of one
attempt, ...)"); the 15 s boundary (declined above).

opus v4: Q1 banned, Q2 banned, Q3 rotated (the carve-out quoted), Q4 rotated, no contradiction.
Its gaps, declined: the outcome of a refused reconnect after an answer and whether a redirect
stays in the attempt (both stated in the cut bullet the excerpt left out: "the budget of one
attempt, connect to last byte, TLS handshake, headers and redirects included", and every
post-answer failure is a cut that rotates); budget equals `--chunk-timeout` (same bullet); where
the 15 s clock starts (declined above); a proxy that accepts, closes without a byte and then
refuses a reconnect (exotic: an http proxy keeps one connection per attempt; recorded, not
worked).

- [x] Final: no undecided gap left on either tier; receipt ended after the commit.
