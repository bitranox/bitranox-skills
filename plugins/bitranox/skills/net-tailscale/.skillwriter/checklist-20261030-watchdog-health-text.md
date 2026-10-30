# Review checklist 2026-10-30: watchdog keyed on the real control-loss Health text

Entry covered: E12, the watchdog paragraph gives no concrete signal, and a probe-failure fallback
that matches the restart pattern restarts `tailscaled` on every tick.

Files: `SKILL.md` (watchdog paragraph in "Boot ordering and staying up", one Common mistakes row).

## Claims and their evidence

- [x] Health text: tailscale `health/warnings.go` at v1.104.4 (latest release),
      `notInMapPollWarnable`: `Text: StaticMessage("Unable to connect to the Tailscale
      coordination server to synchronize the state of your tailnet. Peer reachability might
      degrade over time.")`, `TimeToVisible: 8 * time.Minute`.
- [x] No LocalAPI health endpoint: `ipn/localapi/localapi.go` handler map has no `health`
      entry, and a live read on a local node: `curl --unix-socket
      /var/run/tailscale/tailscaled.sock .../localapi/v0/health` -> 404, control
      `.../localapi/v0/status` -> 200.
- [x] `tailscale status --json` carries a `Health` key (local node, 1.98.3: `Running []`).

## Mechanical checks

- [x] Width and fence check over added lines prints nothing; Common mistakes row fits the
      existing column widths.
- [x] ASCII only, no history-finder hit (no version-scoped wording added), no private host.
- [x] The paragraph after the edit ("## DNS: ...") does not refer back to it.
- [x] redcheck --corpus-cascade: watchdog scenario `clean` (not caught).

## Probes (bitranox:baseline-probe, text only)

- [x] RED (opus, pre-edit text): Q12 reported "'recent control-plane contact' has no JSON field
      and no threshold, so a watchdog cannot be written from it as given"; fallback rule NONE.
- [x] GREEN (opus, edited text): Q12 quoted "restart the unit only when that call times out or
      its `Health` array holds the control-loss warning ..." and the fallback sentence.
- [x] GREEN gap "says to keep a probe that could not run apart from a finding, but not what to do
      with it" -> closed ("A probe that could not run gets a stderr note and no restart.").
- [x] Re-probe on the final text (opus): Q12 quoted that sentence. Remaining gap declined: a
      `timeout ... | jq` pipe hides the timeout exit; the text already says to parse the JSON in
      the watchdog's own language rather than with an external tool, which removes the pipe.
- [x] Haiku arm on the final text: Q12 named all three faults of a guessed `control: offline`
      grep with a `FAIL` regex matching the fallback, and gave the Health-text trigger with the
      quote. Gap declined: the timer interval (the 8-minute visibility delay is stated; the
      interval is the operator's choice).
- [x] Tiers: opus RED, opus GREEN, opus re-probe, haiku final (4 cells).

## Integration note

A parallel release (10.8.1) rewrote the same watchdog paragraph first. This change was merged onto
that text: it keeps 10.8.1's bullets and adds only the 8-minute TimeToVisible fact (measured in
`warnings.go` v1.104.4) as one sentence, plus the Common mistakes row. The rewrite described above
was not shipped.
