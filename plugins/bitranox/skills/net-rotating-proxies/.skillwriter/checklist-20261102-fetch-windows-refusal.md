# skill-writer checklist - net-rotating-proxies (2026-11-02, `fetch` refusal timing on Windows)

One sentence of the ban bullet in `## One large file across proxies` corrected, and one added:
a refused connect was described as "an immediate 'connection refused'" and as banning outright.
On Windows the refusal is reported only after about 2 seconds, so with a `--chunk-timeout` below
that the budget ends the connect first and the proxy is rotated as a cut, not banned. The bullet
now puts the budget condition on refusals and errors alike and says this per OS. Behaviour
unchanged; the description unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval, answered by direct quote,
      `bitranox:baseline-probe` on opus and haiku, the bullet pasted.
- [x] The claim checked against the system: the windows-latest CI cell got `('cut', 0)` for a
      refusing proxy at a 0.5 s budget and an empty `bad.txt` for one at 1.0 s, where Linux and
      macOS got `dead`; the refusal delay (about 2.07 s, Windows retrying a refused SYN itself) is
      a measurement recorded in this tree's memory from a Windows VM. `failure_outcome` returns
      `dead` only for a connect error before the proxy answered, and a budget that ends during the
      connect raises BudgetSpent, a cut. The code is unchanged; the tests now give every refusal
      case a 5 s budget (`REFUSE_BUDGET`).
- [x] RED (the bullet as committed), both tiers, questions: Linux, budget 1, refused -> banned;
      Windows, budget 1, refused -> rotated; Windows, budget 30 -> banned; per-OS timing stated?
      haiku: Q2 "NOT DECIDABLE from the excerpt"; opus: Q2 "BANNED, going by the excerpt's own
      wording" (wrong). Both: Q4 NONE ("The only timing word about a refusal is 'immediate'").
      Both also reported that the first sentence bans a refusal outright while the closing
      sentence adds "before the budget runs out".
- [x] Edit: "refused ("connection refused") or ends in any other error (...), in both cases
      before the attempt's budget runs out", plus "A refusal arrives at once on Linux and macOS,
      but Windows reports it only after about 2 seconds, so there a `--chunk-timeout` under that
      turns a refusing proxy into a cut that only rotates."
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion ("Once a proxy answered ...") still reads on from the new sentence.
- [x] No addresses, hosts or paths added; ASCII only; describes current behaviour only.

## GREEN (the edited bullet): results below.

GREEN, both tiers (Linux budget 1 refused; Windows budget 1 refused; Windows budget 30 refused;
Linux budget 10 silent drop): opus 4/4 and haiku 4/4 by quote, Q2 decided by "Windows reports
it only after about 2 seconds, so there a `--chunk-timeout` under that turns a refusing proxy
into a cut that only rotates". Both reported one real gap: "however long that error takes"
read against "in both cases before the attempt's budget runs out". Fixed: "at any point before
the attempt's budget runs out". Opus also read "or it gets no reply" as possibly the proxy;
fixed: "or the TCP connect gets no reply at all".

- [x] Final re-probe of the final text, both tiers (Windows budget 1 -> rotated; Windows budget
      30 -> banned; Linux budget 10, host unreachable after 3 s -> banned; Linux budget 30,
      accept then silence -> rotated; contradiction?): opus 4/4, haiku 4/4, both quoting the
      deciding sentences; no contradiction, only tensions resolved within the bullet.
- [x] Declined gaps: the exact Windows boundary (2.07 s measured once; "about 2 seconds" is the
      honest precision, a budget near it is a coin toss and the text says "under that");
      "Only a failed connect" against the no-reply rule (the colon list defines what a failed
      connect is); the exact 15.0 s boundary, where the budget starts, what a ban costs in
      attempts, repeated cuts never banning (declined in the fifth-fixes checklist, same reasons);
      what an unbound port produces (the stand-ins and the CI cells show a refusal; both answers
      held either way); OS connect timeouts (Linux SYN retries outlast the 15 s clamp).
- [x] Width and fence check over the added lines printed nothing.
