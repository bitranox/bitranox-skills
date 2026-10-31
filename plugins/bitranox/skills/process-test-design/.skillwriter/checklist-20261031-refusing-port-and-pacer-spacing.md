# Review checklist: process-test-design, refusing port and pacer spacing (2026-10-31)

## Change

Two new bullets under "Deterministic and order-independent":

1. After the listening-socket teardown bullet: a port that must REFUSE a connection comes from
   just below the OS dynamic range (Linux: first number of `ip_local_port_range`; Windows and
   macOS: 49152), confirmed free with a bind that is closed again, never from a released
   `bind(0)`, which another xdist worker's `bind(0)` can be handed. Includes the `refusing_port()`
   helper, the macOS bound-not-listening and Windows ~2 s refusal notes (5 s connect timeout), and
   why the port stays free after the probe (only a fixed-port bind can take it).
2. After the clock-read bullet: assert a pacer's spacing on the instants it schedules from (each
   event's start), not completion stamps; a simulated timeline shows end stamps 0.177 s apart
   while starts are 0.201 s apart.

## Claims and evidence

- [x] Pre-edit text has no rule for either case: RED probe (below) answered NOT COVERED twice;
      `grep -niE "ip_local_port|dynamic range|bind\(0|refus.*port|pacer|start to start"` on the
      pre-edit SKILL.md and `references/` found nothing on either topic.
- [x] Linux dynamic range: `cat /proc/sys/net/ipv4/ip_local_port_range` printed `32768 60999`.
- [x] `bind(0)` reuses released ports: 2000 sequential `bind(("127.0.0.1", 0))` + close calls
      returned 1865 distinct ports, all in 32777..60987 (inside the dynamic range).
- [x] The shipped `refusing_port()` block, extracted verbatim from SKILL.md and executed, returned
      32767, and `socket.create_connection(("127.0.0.1", 32767), timeout=5)` raised
      `ConnectionRefusedError`.
- [x] The shipped pacer block, extracted verbatim and executed, printed `0.201` and `0.177`.
- [x] Inherited, not measured here: macOS ignores a SYN to a bound-not-listening port and Windows
      reports a refusal only after about 2 s (recorded from earlier CI measurements); the 49152
      floor is the Windows and macOS default dynamic range start.

## Probes (bitranox:baseline-probe, haiku, passage pasted, quote-back required)

- [x] RED (pre-edit passage): Q1 port choice NOT COVERED; Q2 pacer spacing NOT COVERED.
- [x] GREEN (edited passage): Q1 quoted "Take a port just below the dynamic range, which
      `bind(0)` never hands out ..." and named 32767 as the first port tried for range
      `32768 60999`; Q2 quoted "A pacer that spaces events start to start promises nothing about
      when they END ..." and "record each event's START in the test ...".
- [x] GREEN gaps closed: why the port stays free between probe and use (added the fixed-port
      sentence); the connect timeout (now "well above that (5 s)").
- [x] Final probe on the final text (haiku, 3 questions): quoted the fixed-port sentence, "(5 s)",
      and "the probe is closed again, so nothing is bound" for not holding the probe socket.

## Gaps declined

- [x] Which fixed ports a given suite uses: the suite's own config decides; the rule names the
      boundary to keep them off.
- [x] Reading the live dynamic range on Windows (`netsh int ipv4 show dynamicport tcp`) and macOS
      (`sysctl net.inet.ip.portrange.first`): the default suffices for the rule; a host that moved
      its range is out of scope for a test helper.
- [x] Probing 0.0.0.0 as well as 127.0.0.1: the test connects to 127.0.0.1, and on Linux a
      wildcard bind on the port already makes the 127.0.0.1 probe fail.
- [x] What to do when the pacer is library code (how to wrap the call): depends on the code under
      test; the bullet gives the two seams.
- [x] A pacer that spaces end to start: covered by the bullet's last sentence (read which instant
      the pacer computes from).

## Mechanical checks

- [x] Width and fence check over the added lines (meta-skill-writer script, plus a non-ASCII scan)
      printed nothing; `reformat_tables.py --strict` reports Unchanged.
- [x] Paragraph after each insertion point read ("No timer in a test", "When the code's own
      deadline kills real child processes"): no back-reference re-bound, no duplicated bullet.
- [x] No private paths, hosts or names; addresses are loopback only. Front matter untouched.
