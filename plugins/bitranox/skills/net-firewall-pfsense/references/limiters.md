# Dummynet limiters that load but shape nothing, and a queue for giving way

Observed on pfSense 2.8.1. Shaping code changes between releases, so re-check each point on
another version before relying on it. Each limiter trap here fails silently: the rule looks right
and nothing is shaped.

## A limiter on a rule with a gateway: reported ignored, not proven

The report is that pfSense ignores a limiter on a rule that carries a per-rule gateway (policy
routing). The loaded ruleset still shows the pipes, `dnpipe(1, 2)` on the rule in `pfctl -sr`, while
`dnctl sched show` stays at 0 active in both directions during a sustained download.

This claim rests on that `0 active` reading alone, which does not prove a limiter idle (see
"Checking that shaping happens"). Before relying on it or clearing a gateway for it, re-test it by
rate against a control.

If the re-test shows it ignored: a floating match rule is not a reliable way around it, because
states are interface-bound and tagged by the rule that creates them, which is still the gatewayed
pass rule. Attach the limiter to a state-creating rule without a gateway. Before clearing a rule's
gateway, find out why it is set: on a single-WAN box it is often redundant, with several WANs it
may be what routes the traffic.

## Write the FQ-CoDel parameters explicitly

The rule generator computes the FQ-CoDel defaults from the `net.inet.ip.dummynet.fqcodel.*`
sysctls before it loads the dummynet module. On a box that has never loaded dummynet those sysctls
do not exist yet, so the generated scheduler line has empty values, `dnctl` aborts with
`quantum needs number`, the first pipe loads as WF2Q+ instead of FQ-CoDel and the second never
loads. Set every parameter in each limiter's `<queue>` element, for example:

```xml
<sched>fq_codel</sched>
<param_fq_codel_target>5</param_fq_codel_target>
<param_fq_codel_interval>100</param_fq_codel_interval>
<param_fq_codel_quantum>1514</param_fq_codel_quantum>
<param_fq_codel_limit>10240</param_fq_codel_limit>
<param_fq_codel_flows>1024</param_fq_codel_flows>
```

## Where limiters live in config.xml

Limiters are under `<dnshaper>`, one `<queue>` element per pipe, with `<name>`, `<number>`,
`<bandwidth><item>` (`<bw>`, `<bwscale>`, `<bwsched>`), `<enabled>`, `<mask>`, `<aqm>`, `<sched>`,
the `param_fq_codel_*` elements and `<ecn>`. A rule names its pipes by limiter name: `<dnpipe>`
for the In direction, `<pdnpipe>` for Out. pfSense emits no pipe for a rule whose `<dnpipe>` is
empty, so a rule with only `<pdnpipe>` set is shaped in neither direction.

Set these in the GUI (Firewall > Traffic Shaper > Limiters, then Apply) or through the config API
in a `pfSsh.php playback` script, after a `snapshot`. `write_config()` alone loads no pipe, so the
script must also call `filter_configure()` (or run `/etc/rc.filter_configure_sync` afterwards). If
you edit `config.xml` by hand instead, use an XML parser and then reload as SKILL.md's "Not covered
here" says (`rm -f /tmp/config.cache && /etc/rc.filter_configure_sync`); until then nothing
changes.

## Checking that shaping happens

The proof is the measured rate against a control, plus the byte and queue counters in
`dnctl pipe show`, not a pipe shown on the rule in `pfctl -sr`. A pipe missing from
`dnctl pipe show` did not load; a listed one may be a leftover (below).

`0 active` in `dnctl sched show` does not prove idle. Measured during a download capped at
9.5 Mbit/s by a 10 Mbit FQ-CoDel limiter on a rule without a gateway, with a control host on the
same LAN at 19 Mbit/s: it read `0 buckets 0 active` on both pipes while `dnctl pipe show` counted
5.9 MB and 36 queued packets through the download pipe.

A control behind the same public IP as the load must use a different server: a speed-test mirror
answered the control with 0 bytes while the load ran, which reads as total starvation.

A pipe listed in `dnctl pipe show` does not prove a limiter exists. Removing limiters from
`config.xml` and reloading leaves their pipes listed, with no rule referencing them, and
`dnctl -q pipe flush` did not clear them either.

`pfctl -sq` indents queue names with several spaces, so a check that greps for `queue <name>` with
one space reports a present queue as missing. Match the name alone: `pfctl -sq | grep -i <name>`.

## Giving way with no cap: an ALTQ priority queue

When a host should yield to others but keep the line when it is idle, a low-share ALTQ queue fits
better than a limiter, which caps it either way. Adding a queue reloads the shaper, which may touch
live VoIP, so check for calls first.

1. Add a low-share leaf queue under the parent on both WAN and LAN.
2. On the host's LAN rule, set the queue and a tag.
3. Add a floating WAN match rule with `tagged <tag>` that sets the queue, placed AFTER any
   port-based match rules: the last match wins, and those would otherwise re-classify the host's
   upload.

An A/B toggle must clear the queue on BOTH rules: leaving either one kept the host in the queue and
produced two identical arms. Read `pfctl -vsq` per arm to prove classification.

Expect a modest gain. Measured, n=2 per arm, without the queue then with it: control 15 then
16 Mbit/s, worst-case response 0.4-0.5 s then 0.3 s. The share the HFSC weights predict (5:1) did
not appear (about 2:1), reason not established.
