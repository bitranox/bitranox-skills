# checklist - the pre-bind index must match the index the boot disk lands on

New skill. Its load-bearing claim: under `scsihw=virtio-scsi-single` PVE gives every disk its own
virtio-scsi controller at a PCI address derived from the scsi index, Windows enumerates one device
instance per address, and the boot loader binds `vioscsi` only to an instance it has already seen.
So a pre-bind scratch disk at the wrong index produces INACCESSIBLE_BOOT_DEVICE 0x7B.

## RED

- [x] Baseline run on the target scenario (move a Windows boot disk from `sata0` to virtio-scsi),
      pinned to a weak-literal tier, with the skill withheld and the trap NOT spelled out. The
      prompt supplied every fact a competent admin would have, including `scsihw` unset and
      `vioscsi Start=0`, and asked the index question neutrally among two others.
- [x] The baseline FAILED in the exact way the skill exists to prevent, and did so confidently:
      it prescribed `qm set <vmid> --scsi1 <storage>:4,...` with the comment "scsi1, not scsi0, so
      it never collides with the boot-disk slot you're about to use", then moved the boot disk to
      `scsi0`. That sequence is the one that bugchecks.
- [x] Asked directly, it answered "Functionally, no - Windows and the vioscsi driver don't care
      what LUN/index number they're attached at; the guest boots identically from any valid index."
- [x] It reached the correct mechanism and then inverted the conclusion: "Each `scsiN` index gets
      its *own* virtio-scsi-pci controller/PCI device under `virtio-scsi-single`" followed by
      "That's invisible to Windows." A skill that only asserted the rule without naming this
      inversion would leave the reasoning that defeats it intact.
- [x] Baseline contamination ruled out: the answer is wrong in the decisive place, so no
      environment or prompt leak supplied it. The parts it got right (`scsihw` absent defaults to
      `lsi53c895a`, `Start=0` is not sufficient, pre-bind before moving) are genuine prior
      knowledge and are therefore NOT what the skill spends its words on.

## GREEN

- [x] Same scenario, same tier, skill supplied. The index answer reversed to "Yes, decisively",
      the pre-bind moved to `scsi0`, and the verification step required the `0820F0` suffix before
      touching the boot disk.
- [x] The other two questions also landed: `Start=0` not sufficient, and 0x7B diagnosed as an
      enumeration mismatch rather than a missing driver.
- [x] Both runs were required to end with a `Skill gaps` section, and both lists are worked below
      rather than treated as a pass.

## REFACTOR

- [x] GREEN produced a sharper statement of the trap than the draft had, and it is now in the
      text: the wrong-index scratch disk "would itself look perfectly healthy the entire time".
      That is what makes the mistake survive review, so it is stated as its own paragraph.
- [x] Gap closed - the mechanism was scoped to `virtio-scsi-single` with nothing said about plain
      `virtio-scsi`. Added: the shared controller has one instance so the index stops mattering,
      at the cost of per-disk `iothread`.
- [x] Gap closed - the address table stopped at `scsi3` with no rule for a fifth. Added
      `device = index + 1`, suffix is that shifted left three bits, with `scsi4` worked through.
- [x] Gap closed - "check `bcdedit` for a leftover safeboot" named the check but not the fix.
      Replaced with both commands, the second marked conditional.
- [x] Gap closed - "confirm with a second reboot" did not say what counts as booted. Now states
      the workload must return, not a logon screen and not `qm status: running`.
- [x] Diffed GREEN against RED in BOTH directions. RED distinguished `0xc0000001` (boot manager
      or BCD, pre-kernel) from `0x7B` (kernel-stage driver); GREEN collapsed them because the
      draft's own table did. That is a lost diagnostic result, not an acceptable trade, so the
      distinction is restored with the WinRE `diskpart` check that separates them.
- [x] Gaps DECLINED with reason: a snapshot-before-change policy and a snapshot soak period are
      site policy, not storage tuning, and belong to whoever owns the change process; missing
      storage names and volids in the scenario are the scenario's, not the skill's.
- [x] Every measured number carries its conditions (single-vdev NVMe pool, `ashift=12`, QEMU 11,
      DiskSpd 2.2, 16 threads at QD8, ARC evicted cold, three interleaved reps) and is framed as a
      direction rather than a constant.
- [x] The skill states what is NOT sufficient as explicitly as what is, because all three of
      `Start=0`, a healthy PnP-time controller, and a CriticalDeviceDatabase entry can hold while
      the move still fails.
- [x] Scope is stated in the frontmatter, the opening paragraph, and a table: QEMU/KVM only. The
      table names which findings transfer to a different VMM device model and which do not, so a
      later sibling skill starts from the split rather than re-deriving it.
- [x] ASCII only, no em-dashes or typographic tells. No session narrative, no scratch paths, no
      addresses, hostnames or VMIDs from any real machine - examples use VMID 100 and
      `local-zfs`.
