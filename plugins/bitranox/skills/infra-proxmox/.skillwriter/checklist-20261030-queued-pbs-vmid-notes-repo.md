# Review checklist 2026-10-30: queued contributions (PBS tokens, VMID change, Notes, repo, CT create)

Entries covered:

- E3 PBS CLI: `generate-token` has no `--output-format`, `Result: {...}` output, token rights are
  an intersection, `proxmox-backup-debug api` in scripts.
- E4 full clone from a zfspool snapshot (partly refuted, see below) and guest-agent freeze.
- E6 `pveam available` lists arm64 builds; `pct create` nesting warning for systemd 257.
- E7 changing a VM's VMID while keeping snapshots.
- E9 where a VM's Notes live in the conf.
- E11 reading the PVE package repository from a script.

Files: `SKILL.md` (six troubleshooting rows, two index rows), `references/zfs-guest-disks.md`
(full-clone refusal text, new section "Changing a VM's VMID"), new
`references/package-repo-from-script.md`.

## Claims verified against source or a live read-only endpoint

- [x] E4: `qm clone --full --snapname` on zfspool REFUSES; it does not copy the current state.
      qemu-server `src/PVE/API2/Qemu.pm` clone_vm: `$msg .= " a snapshot of" if $snapname;` then
      `die "Full $msg\n" if !PVE::Storage::volume_has_feature($storecfg, 'copy', $volid, $snapname, $running)`;
      pve-storage `ZFSPoolPlugin.pm` volume_has_feature: `copy => { base => 1, current => 1 }`,
      `$key = 'snap'` when a snapname is passed. So the entry's "always copies the CURRENT state"
      is wrong; the refusal text was added instead.
- [x] E4 freeze/thaw: already in `ch10-qemu/vm-settings-advanced.md:116-124` ("An fs-freeze will
      be issued ... Taking a snapshot without RAM of a running VM"). No change.
- [x] E3: PBS command-syntax page: `proxmox-backup-manager user generate-token <userid>
      <token-name>` lists only `--comment`, `--digest`, `--enable`, `--expire` (no
      `--output-format`); `user permissions <auth-id>` has `--output-format` and `--path`;
      `proxmox-backup-debug api create <api-path>` has `--output-format`. PBS user-management page:
      "Result: {" example output, and "The resulting permission set on a given path is then
      intersected with that of the corresponding user ... API tokens can never do more than their
      corresponding user". The 4.2.8-specific panic was not reproduced; the row states only the
      general rule (read state before retrying a failed text-output call).
- [x] E6: `http://download.proxmox.com/images/aplinfo-pve-9.dat` lists
      `system/debian-13-standard_13.6-1_amd64.tar.zst` and `..._arm64.tar.zst`. pve-container
      `Setup/Base.pm` check_systemd_nesting: `return if $features->{nesting}` ... `return if
      !defined($sdver) || $sdver <= 241;` `return "Systemd $sdver detected. You may need to enable
      nesting.";`. pve-manager `www/manager6/lxc/CreateWizard.js`: checkbox `inputValue:
      'nesting=1', value: true`, `disabled: '{!unprivileged}'`.
- [x] E7: pve-manager `API2/Cluster.pm` nextid: "Pass a VMID to assert that its free" and
      `raise_param_exc({ vmid => "VM $vmid already exists" })`. qemu-server `CLI/qm.pm` rescan
      has `dryrun` ("Do not actually write changes out to VM config(s)"). Other files naming a
      VMID taken from `appendix-c-config-files.md` path map (firewall/{vmid}.fw, jobs.cfg,
      ha/resources.cfg, user.cfg) plus replication.cfg.
- [x] E9: qemu-server `QemuServer.pm` write_vm_config: "add description as comment to top of
      file", `$raw .= '#' . PVE::Tools::encode_text($cl)`; keys loop skips `description`.
      pve-guest-common `AbstractConfig.pm` __snapshot_copy_config: `next if $k eq 'description';`.
      `CLI/qm.pm` config printer: `if ($k eq 'description') { $v = PVE::Tools::encode_text($v); }
      print "$k: $v\n";`. Also stated upstream in `ch10-qemu/configuration-options.md:168-170`.
- [x] E11: `curl https://download.proxmox.com/...InRelease` exit 60 ("no alternative certificate
      subject name matches"); `openssl s_client` shows `CN=enterprise.proxmox.com` with SANs
      `*.cdn.proxmox.com` hosts; enterprise InRelease and pve-no-subscription Packages.gz both
      401; signed `Components: pve-no-subscription pve-test`; `pvetest/binary-amd64/Packages.gz`
      answers 200. Key from `https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg`:
      `fpr:::::::::24B30F06ECC1836A4E5EFECBA7BCD1420BFE778E:`. `gpgv` with a wrong keyring: rc=2
      and `--output` file still written (3475 bytes); with the right key rc=0. Text prepended
      before the signed block: rc=0, prepended text absent from the output. Packages.gz sha256
      `6ae54ac4...88e0` matches the signed SHA256 list. Packages lists `pve-manager` 9.0.0~10,
      ~11, ... (old versions stay); `Filename: dists/trixie/pve-no-subscription/...`.

## Mechanical checks

- [x] Every added table row padded to the existing column widths; reformat_tables.py on a copy
      reports `Unchanged` (canonical).
- [x] Width and fence check over added lines (script from meta-skill-writer): prints nothing for
      SKILL.md and zfs-guest-disks.md; new reference file has no line over 100 columns.
- [x] ASCII only: `git diff -U0 | grep '^+' | LC_ALL=C grep -cP '[^\x00-\x7f]'` prints 0.
- [x] Latest-release finder over added lines: no hit.
- [x] No private host, path or address in added text (grep for IPs, /home/, /media/: no hit).
- [x] Paragraph after each insertion point read: "Rollback only to the LATEST snapshot" still
      points to "next section" = Full clone; no back-reference re-bound.
- [x] redcheck --corpus-cascade on the VMID, Notes and repo scenarios: VMID and Notes clean
      (not caught); repo scenario flagged the tree-top CLAUDE.local.md on shared terms
      (`parses`, `proxmox`, `repository`, `verifies`); opened it: no line on gpgv, the repo
      certificate or pve-test, so it is a term overlap, not inherited.

## Probes (bitranox:baseline-probe, text only)

- [x] RED (opus, pre-edit excerpts): Q4 refusal message NONE ("I would guess something like
      ..."); Q5 VMID procedure NONE; Q6 Notes NONE; Q7 repo NONE; Q8 arm64/nesting NONE; Q9 PBS
      token NONE.
- [x] GREEN (opus, edited excerpts): each of Q4-Q9 answered with a direct quote of the new text
      (e.g. Q4 quoted "so the clone refuses with `Full clone feature is not supported for a
      snapshot of '<volid>' (<disk>)` before copying anything").
- [x] GREEN gaps worked: Q5 "no step says when to stop the VM relative to removing it from HA"
      and "no concrete action for firewall/501.fw" -> closed (intro "Do steps 1 and 2 first, then
      stop the VM"; step 2 names the rename of `firewall/<old>.fw` and when to re-add HA).
      Declined: Q4 "no procedure for carrying a whole snapshot config across" (pre-existing
      section, out of this change's scope); Q8 privileged CT nesting (the warning text and GUI
      default concern unprivileged; leaving the privileged case unstated rather than inventing
      policy); Q9 where to store the secret (generic secret handling, owned elsewhere).
- [x] Re-probe on final text for the touched question and haiku arm: see below.

## Extra item: per-tool `command -v` in "Fresh PVE 9 node gaps"

- [x] Claim measured locally: bash `command -v git nonexistent_zz` and `command -v nonexistent_zz
      git` both rc=0; dash `command -v nonexistent_zz git` rc=127 printing nothing, dash
      `command -v ls nonexistent_zz cat` printed only `/usr/bin/ls`, rc=0. The loop
      `for t in git nonexistent_zz; do command -v "$t" >/dev/null || echo "missing: $t"; done`
      printed `missing: nonexistent_zz`.
- [x] Row text now: "check each tool alone (`for t in git rsync; do command -v "$t" >/dev/null
      \|\| echo "missing: $t"; done`; one `command -v git rsync` can pass with one missing)".
      Pipes escaped as in the table's other rows; cell fits the column; formatter `Unchanged`.

## Re-probes on the final text

- [x] Opus re-probe after the first fix round (Q5 VMID order and firewall): quoted "Do steps 1
      and 2 first, then stop the VM" and the firewall rename sentence. New gaps it raised:
      `grep -rnw` matches contents, so a firewall file holding no id is not found -> closed
      (`ls /etc/pve/firewall/<old>.fw` added to step 2); no HA command -> closed
      (`ha-manager remove vm:<old>`, sid form from `appendix-a-cli/ha-manager.md` "<sid>:
      <type>:<name> ... example: vm:100"); how to edit jobs.cfg/user.cfg -> closed ("writing each
      of those files whole too").
- [x] Haiku arm (7 questions, Q1 Q2 Q4 Q6 Q7 Q8 Q9): every answer quoted the new text; no wrong
      action. Its gaps were about excerpt framing (sections not shown), declined as excerpt
      artifacts.
- [x] Final haiku re-probe (QA command -v, QB VMID): QA quoted the per-tool loop and said `ok`
      "does not prove both are there"; QB ordered pvesh check, `ls` of the firewall file,
      `ha-manager remove vm:501`, stop, rename, whole-file edits, verify, re-add HA. Gaps
      declined: the loop's exit status (the loop exists to PRINT the missing names, and the text
      says to read them); the jobs.cfg entry format (the reader edits the file it just grepped);
      installing on the node itself (pre-existing row text, not this change); a VMID taken
      between check and rename (a race no CLI step closes, out of scope).
- [x] Tiers and cells for this skill: opus RED, opus GREEN, opus re-probe, haiku GREEN, haiku
      final re-probe (5 cells).
