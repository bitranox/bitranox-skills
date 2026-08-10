# skill-writer checklist - infra-modulejail (2026-08-10, edit: runtime-loaded modules)

Adds the discovery method for modules the dependency closure cannot predict, plus three verified
traps. Existing sections unchanged apart from the description and the mistakes table.

## RED - baseline on the CURRENT skill text

A sealed subagent (sonnet) received the shipped skill and a scenario: on a modulejail host, a
`systemd-zram-generator` device configured for `zstd` fails with "Dependency failed", `swapon`
shows nothing, `lsmod` is empty, and `modprobe zram` prints nothing and exits 0.

It diagnosed the block correctly and named the right proving command. Then it FAILED on the
question the edit exists for - which modules to whitelist:

- It asserted `zsmalloc` is "a genuine hard module dependency ... so `modprobe --show-depends`
  surfaces it". On the measured kernel `zsmalloc` is a module but is NOT a listed dependency of
  `zram` and is never loaded.
- It gave `zstd`, `zstd_compress`, `zstd_decompress` as the backend set. Only `zstd.ko` exists;
  `modinfo zstd_compress` answers through an alias, which is what makes the guess survive a
  check.
- Its own gaps section states the cause: "The skill's core method ... has no step for modules
  pulled in via runtime `request_module()` ... Following the skill exactly unblocks zram itself
  but silently leaves the zstd backend jailed; the failure would just move, not resolve."

That is the gap, in the baseline's own words, and it is why the edit teaches a discovery method
rather than a module list.

## Ground truth used in the text (measured, not recalled)

    kernel 7.0.2-7-pve
    modinfo -F depends zram  ->  lz4hc_compress,842_decompress,lz4_compress,842_compress
    zsmalloc                 ->  IS a module, NOT a dep of zram, not loaded
    find ... -iname '*zstd*' ->  zstd.ko only
    zram running [zstd], compressing 4096 -> 64 bytes, with zstd NOT loaded
    modulejail --dry-run     ->  stdout 1 line, 0 install-lines; stderr 6725 install-lines

## GREEN - same scenario, edited text

The subagent refused to reuse the example ("Do not reuse the skill's worked-example module list -
it is explicitly kernel-specific"), ran `--show-depends` on the host, exercised the real path,
read `journalctl -t modulejail`, and looped until the refusal list is empty. Asked whether a
working zram device proves nothing is blocked, it answered "No" and listed the checks, including
inspecting the kernel config for a built-in backend.

## GREEN gaps - closed or declined

- [x] CLOSED. "Internal contradiction on the block's observable behavior" - the text claimed
      `install X /bin/true` "returns 'no such module'". Wrong: it exits 0 silently. Rewritten,
      and the two distinct failure shapes (silent block vs `Unknown symbol` for a blocked
      dependency of a kept module) are now tabled.
- [x] CLOSED. zsmalloc read as "a module to go and find". Rewritten as an explicitly WRONG guess,
      alongside the `modinfo`-answers-via-alias trap.
- [x] CLOSED. `reset-failed <unit>` too generic. Now names the unit chain and asserts on
      `swapon --show` rather than on the unit going active.
- [x] DECLINED. "Block-list generation step is never shown" - it is, in step 2 of the shipped
      skill; the baseline saw an excerpt.
- [x] DECLINED. "Cold-reboot gate asserted but not explained" - explained in step 5 of the
      shipped skill; excerpt artifact.
- [x] DECLINED. Interpreting systemd dependency chains in general - owned by systemd knowledge,
      not this skill. The one case that recurs here is named.

## Both directions

No baseline result is missing from GREEN: every RED finding (block diagnosis, proving command,
regenerate-and-retry) reappears, and the module list moves from guessed to derived.

## Checks

- [x] Name unchanged, valid characters
- [x] Frontmatter: name + description only; description trigger-first, under 1024 chars
- [x] Description adds distinctive symptoms (modprobe exits 0 loading nothing, lsmod empty,
      "Dependency failed", "blocked: <module>") without summarising the workflow
- [x] Every command in the new sections executed on a real host, not reviewed
- [x] No invented module list shipped as fact; the kernel-specific warning is explicit
- [x] Reserved/for-example values only; no host addresses, MACs or private paths added.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/'` clean
- [x] No session narrative or operator provenance
- [x] Cross-reference to `bitranox:infra-swap-tuning` uses the skill name, no `@` link
- [x] Security: no secrets, credentials, hostnames or PII in the diff; no new scripts shipped
- [x] Hub rules not applicable - self-contained SKILL.md, no supporting files
