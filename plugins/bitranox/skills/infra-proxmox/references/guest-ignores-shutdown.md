# Linux Guest Ignores `qm shutdown`

Symptom: `qm shutdown <vmid>` or the GUI Shutdown button does nothing visible in a Linux guest, and
the task times out (or a job waiting for a graceful stop waits out its whole timeout).

Without the QEMU guest agent, `qm shutdown` presses the ACPI power button: it sends an ACPI event
and relies on the guest OS to act on it. A guest with no handler for that event ignores it. With
the guest agent enabled (`agent: 1`) and running, Proxmox VE sends the shutdown through the agent
instead (`ch10-qemu/vm-settings-advanced.md`, QEMU Guest Agent), so the ACPI path below does not
apply.

## Minimal guests: no acpid

A minimal Alpine Linux guest ships no `acpid`, so it ignores the button. Install and enable it:

```sh
apk add acpid
rc-update add acpid default
rc-service acpid start
```

Its default handler (`/etc/acpi/handler.sh`) maps `button/power` to `poweroff`. Alpine's busybox
has no `shutdown` command; the clean commands inside the guest are `poweroff` (or `halt -p`,
`reboot`).

## When acpid is installed and the button still does nothing

Check whether the kernel registered the power button at all. QEMU's power button is an ACPI
fixed-event button (`LNXPWRBN`). A kernel can carry the conversion of the ACPI button driver to a
platform driver without the change that registers platform devices for fixed-event buttons
(upstream `ab06eb920401`, "ACPI: scan: Register platform devices for fixed event buttons"). Then
the button gets no driver, acpid never sees a press, and `qm shutdown` times out. Observed on
Alpine's 6.18.57 and 6.18.58 stable kernels, with 6.18.56 still working. The tells, read in the
guest:

- `/sys/bus/acpi/devices/LNXPWRBN:00` has no `driver` link (and no `physical_node`);
- `/sys/bus/platform/drivers/acpi-button/` lists no device;
- `/proc/bus/input/devices` has no "Power Button" entry.

Workaround: load the stock `tiny_power_button` module, which is an ACPI driver and still binds
`LNXPWRBN` on such a kernel, and make it send the signal busybox init treats as poweroff
(signal 12, `SIGUSR2`):

```sh
echo 'options tiny_power_button power_signal=12' > /etc/modprobe.d/tiny-power-button.conf
echo tiny_power_button >> /etc/modules
modprobe tiny_power_button   # takes effect now; the two lines above cover later boots
```

On a kernel that registers the button properly, `acpi-button` takes the event first and the
module stands aside. Remove both lines once the guest kernel carries the fix; check for it rather
than assume a version.

Verify with `qm shutdown <vmid> --timeout 30`: the guest must stop within the timeout.

A job that installs a kernel update, reboots into it and then stops the guest gracefully fails at
that final stop: the first broken run is the one that INSTALLED the kernel, not a later one. On a
VM kept as a template or rolled back to a snapshot,
the fix must be baked into that snapshot (roll back, boot, install, stop gracefully, re-take the
snapshot), or every rollback loses it.
