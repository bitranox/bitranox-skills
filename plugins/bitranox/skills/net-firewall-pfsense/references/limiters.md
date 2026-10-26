# Dummynet limiters that load but shape nothing

Observed on pfSense 2.8.1. Shaping code changes between releases, so re-check each point on
another version before relying on it. Each of these fails silently: the rule looks right and
nothing is shaped.

## A limiter on a rule with a gateway is ignored

pfSense ignores a limiter on a rule that carries a per-rule gateway (policy routing). The loaded
ruleset still shows the pipes, `dnpipe(1, 2)` on the rule in `pfctl -sr`, while `dnctl sched show`
stays at 0 active in both directions during a sustained download.

A floating match rule is not a reliable way around it: states are interface-bound and tagged by
the rule that creates them, which is still the gatewayed pass rule. Attach the limiter to a
state-creating rule without a gateway. Before clearing a rule's gateway, find out why it is set:
on a single-WAN box it is often redundant, with several WANs it may be what routes the traffic.

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

The proof is `dnctl pipe show` (every pipe loaded) and `dnctl sched show` (active flows under
load), not a pipe shown on the rule in `pfctl -sr`.

`pfctl -sq` indents queue names with several spaces, so a check that greps for `queue <name>` with
one space reports a present queue as missing. Match the name alone: `pfctl -sq | grep -i <name>`.
