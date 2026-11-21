# skill-writer checklist - net-firewall-pfsense (gateway alarm state flush, remote change guard, shaper rate, per-host fairness)

- [x] Type: technique and reference. Tested with application and retrieval scenarios.
- [x] Step 0b: `skill_decisions.py show --kind rejected,removed --full` printed nothing; no live
      rule's anchor is touched by this change.
- [x] Ground truth read on a pfSense 2.8.1 box (read-only): `filter.inc` state-kill loop (only `all`
      reaches `pfctl -Fs`; `down` globally or per gateway runs `pfctl -M -k gateway -k <gwip>`;
      `none`, `monitor_disable`, `action_disable`, `force_down` skip the gateway); `gwlb.inc`
      passes `-C rc.gateway_alarm` to dpinger only without `action_disable`, starts dpinger only
      for a gateway whose interface has an address, defaults `latencyhigh` 500 and `losshigh` 20;
      `rc.gateway_alarm` reloads dyndns, IPsec, OpenVPN and the filter; `rc.kill_states` (PPP
      link-down) tests the element with `isset`, so an empty or `none` value still flushes there;
      GUI labels from `system_advanced_misc.inc`; `shaper.inc` CoDel defaults from
      `net.inet.ip.dummynet.codel.*`; `filter.inc` emits `dnqueue(` for a child queue;
      `daemon` usage names `-p` the child pidfile; `kern.hz` 100 on a VM.
- [x] FreeBSD `dn_sched_fq_codel.c`: `fq_codel_classify_flow` hashes protocol, addresses and ports
      with a perturbation, no mask.
- [x] config.xml paths named in the text found in a real config: `gateways/defaultgw4`,
      `filter/rule/gateway`, `staticroutes/route/gateway`, `system/dns1gw`,
      `system/gw_down_kill_states`, `gateway_item/action_disable`; `gateways/gateway_group` read
      in `gwlb.inc`.
- [x] Guard commands executed as a shell simulation (setsid sh, pidfile of the sh): ok file then
      `pkill -P <pid> sleep` ends the guard with no rollback; `pkill` without the file runs the
      rollback at once; killing the sh leaves the sleep with parent 1. The pfSense rollback branch
      (`rc.reload_all` on the old file) is not exercised and the text says so.
- [x] RED text check (pre-edit SKILL.md + limiters.md): `gw_down_kill_states`, `action_disable`,
      `dpinger`, `line rate`, `per host`, `5-tuple`, `dnqueue`, `kern.hz`, `dead-man`,
      `daemon -f`, `rc.reload_all`, `failover`, `iface_array`, `setup_gateways_monitor` all 0.
- [x] RED behavioural (opus, pre-edit text, 8 questions): Q1, Q2, Q4, Q7, Q8 NONE; Q3 no safety net
      (snapshot only); Q5 run as playback (the trap the case defeats); Q6 no rate guidance.
- [x] GREEN behavioural (opus and haiku, edited text, same 8 questions, 2 cells): every question
      answered with a verbatim quote of the new text.
- [x] Diff GREEN against RED both ways: nothing lost; RED's site-change-rule and snapshot advice
      still present in GREEN answers' source text.
- [x] Gaps closed from GREEN: empty value needs no change (stated); `php -f` form of the detached
      call; GUI locations of both settings; firewall rules, static routes and gateway groups added
      to the places that name a gateway.
- [x] Gaps declined: a fixed shaper rate margin (recorded as rejected, measured 93-95% kept idle
      ping); WF2Q+ child-queue XML element names (no verified XML here, the GUI builds it); a
      command to tell a missing-address gateway from a failed monitor (the text names both causes);
      the concrete edit command for removing a gateway (task-specific, the skill's XML-parser and
      playback guidance covers it); the guard window length and cleanup of its files (example
      value, operator choice); whether either single-WAN setting alone suffices (not measured);
      a limiter on a gatewayed rule for the WF2Q+ build (the first section of limiters.md covers
      every limiter).
- [x] Final re-probe (opus and haiku, 5 questions on the touched text, 2 cells): all answered by
      verbatim quote; only declined gaps reported.
- [x] Width and fence check over added lines prints nothing; paragraph after each insertion read;
      no non-ASCII added; history-word finder over added lines: no hits.
- [x] Description unchanged. Routing not retested.
- [x] Cases decided beyond the entries: none beyond what the sources state.
- [x] ASCII only, present tense, no private host, repo or path in the added text.
- Decisions: d-20261121-1bf02432, d-20261121-7538db8d, d-20261121-57fd5569, d-20261121-f9f69fa5, d-20261121-ce71b211, d-20261121-3f7e19df
