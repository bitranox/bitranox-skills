# skill-writer checklist - net-firewall-pfsense (2026-10-29, backlog 830)

Change: the Traps paragraph "After `services_unbound_configure()`, restart unbound and check that
it answers" now says `dns add` / `dns rm --apply` restart and verify unbound themselves and exit 2
when it does not answer; the manual restart-and-resolve steps are kept for a hand edit or any other
call of the reconfigure.

- [x] Premise checked against the bundled script, `scripts/pfsense.py`:
      - `cmd_dns_add`: `result["unbound"] = restart_and_verify_unbound(target, name=f"{host}.{domain}", ip=args.ip, ...)`
      - `cmd_dns_rm`: `probe_name, probe_ip = _probe_after_removal(overrides, entry["fqdn"])` then
        `restart_and_verify_unbound(target, name=probe_name, ip=probe_ip, ...)`;
        `_probe_after_removal` returns a remaining override, else `return "localhost.", "127.0.0.1"`.
      - `restart_and_verify_unbound` runs `UNBOUND_RESTART = "pfSsh.php playback svc restart unbound"`,
        then `host <name> 127.0.0.1`, and raises `PfsenseError` "... was written to config.xml, but
        unbound is not answering ..."; `main()` maps `PfsenseError` to `return 2`.
- [x] RED (pre-edit text, `git show HEAD:`): "reconfigure again did not bring it back), and `dns
      add` and `dns rm` with `--apply` call it too. Run `pfSsh.php playback svc restart unbound`,
      then resolve a name on the box" - tells the reader to repeat what the verbs already do.
- [x] GREEN (quote-back): "`dns add` and `dns rm` with `--apply` do this themselves: after the
      write they restart unbound and resolve a name through `127.0.0.1` ... and when unbound does
      not answer they exit 2 saying the change is already in `config.xml`, so repair the resolver
      rather than retry the edit. After a hand edit or any other call of the reconfigure, do it
      yourself".
- [x] `tests/test_pfsense.py::test_skill_md_tells_the_reader_the_same_commands_the_verbs_run`
      still passes (both commands remain in SKILL.md); the skill suite: 174 passed.
- [x] Frontmatter unchanged; ASCII only; no address, host or private path added (`127.0.0.1` is
      the loopback the verbs probe).
- [x] Not a mirrored skill (`repo-gate.py --mirrors` lists no twin for it).
