# skill-writer checklist - net-firewall-pfsense (Trap: filter_configure_sync in a php -f script)

- [x] Premise: the removal route for port forwards and rules already ships ("Retiring a host",
      "no verb removes Forwarder entries, port forwards or rules ..."); only the reload trap was
      missing.
- [x] Change: one Trap paragraph - a `php -f` script calling filter_configure_sync() after
      write_config() fatal-errors on 2.8.1 without shaper.inc; reload with
      /etc/rc.filter_configure_sync and the unbound playback restart, then read live state back.
- [x] Not reproducible here (needs a pfSense box); worded as observed on 2.8.1 with the function
      and file named.
- [x] RED text check (origin/master): `shaper.inc` 0.
- [x] GREEN quote-back: "Do not reload from inside the script: after `write_config()`, run
      `/etc/rc.filter_configure_sync` and `pfSsh.php playback svc restart unbound` as separate
      commands".
- [x] Description: unchanged (314 chars).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
