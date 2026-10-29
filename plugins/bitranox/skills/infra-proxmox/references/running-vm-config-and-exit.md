# A running VM: what `qm set` really does, devices that need a cold start, and how it ended

Measured on PVE 9 (qemu-server 9.2); re-check on another release before building on a detail.

## `qm set` on a RUNNING VM is not just a pending change

`qm set <vmid> -<key> <value>` against a running VM runs `vmconfig_hotplug_pending`: every key that
the VM's `hotplug` option covers (default `network,disk,usb`) is HOT-PLUGGED into the live guest at
once, and a hotplug error makes the command fail. Only the keys that cannot be hot-plugged stay
`[PENDING]`. So restoring a saved config with `qm set` on a VM you only THINK is stopped changes
the running guest's NICs and disks under it.

- `qm start` applies the pending keys (`vmconfig_apply_pending`), except for a start from a saved
  state (resume, `--statefile`), which skips it.
- `qm rollback` rebuilds the config from the snapshot and drops both the live values and every
  `[PENDING]` entry.
- `qm config <vmid>` shows the pending value MERGED in; `qm config <vmid> --current` shows what the
  running guest has. `qm pending <vmid>` lists both side by side.

Before restoring keys, confirm the VM is stopped and its stop TASK has finished (see
`pve-tasks.md`), or restore only keys you are willing to hot-plug.

## An IDE or SATA CD-ROM needs a cold start

`qm set <vmid> -ide2 <storage>:iso/<file>.iso,media=cdrom` on a running VM exits 0 and writes the
config, but the QEMU process never gets the drive: hotplug covers virtio and SCSI, not IDE or
SATA. A reboot INSIDE the guest does not help either, because it does not restart QEMU. Only a full
stop and `qm start` brings the drive in (`qm shutdown`, never `qm stop`, for a Windows guest).

Verify from inside the guest that the drive exists before concluding the media is missing (Windows:
`Get-Volume | Where-Object DriveType -eq CD-ROM`). Check `boot: order=` first: a bootable install
ISO added to a UEFI VM can boot into Setup unless the system disk comes before the CD-ROM.

## How did a VM end: guest power-off, `qm stop`, or a kill?

The usual signals cannot tell. `scope: Deactivated successfully` appears for all three, a killed
QEMU leaves no segfault line, and `qmeventd`'s default log has only `Starting cleanup` /
`Finished cleanup`; its `read: Connection reset by peer` follows a power-off AND a `qm stop`, so it
marks neither.

Two signals that do separate them:

- **`qmeventd -v`.** Run it verbose with a systemd drop-in that repeats `ExecStart` with `-v`. It
  then logs `<vmid>: executing cleanup (graceful: G, guest: g)`:

  | Ending                           | graceful | guest |
  |----------------------------------|----------|-------|
  | the guest powered itself off     | 1        | 1     |
  | `qm stop`                        | 1        | 0     |
  | QEMU killed (`kill -9`, a crash) | 0        | 0     |

  A kill is also preceded by `pid<N>: got EOF`.
- **The tap device's kernel line, in default mode.** A QEMU killed by an unhandled signal
  (SIGKILL, SIGSEGV, SIGABRT) never runs its tap downscript, so the kernel logs
  `tap<vmid>i<N> (unregistering): left allmulticast mode` (Linux bridge; with Open vSwitch
  `left promiscuous mode`). A clean exit or SIGTERM logs the same line WITHOUT ` (unregistering)`.
  Needs a bridged NIC and kernel 6.3 or later, which adds that suffix. Measured: kill 6 of 6 showed
  it, power-off and `qm stop` 0 of 7.

Search with `journalctl _TRANSPORT=kernel --since ...`, not `journalctl -k`, which reads only the
current boot.
