# A Restored CT as a New Machine

`pct restore` of another machine's backup into a new CT id brings far more of that machine than
its data, and none of it shows while the CT is stopped: everything reads normal until the first
start, when it surfaces as a DHCP collision, a mail alert from the wrong host, or a deploy that
overwrites this machine with the other one's config. When the new CT is to be a separate machine
while the source keeps running on the same network, strip the inherited identity OFFLINE, before
the first start, so the copy never runs on the source's LAN.

Work against the stopped rootfs: `pct mount <id>` mounts it under `/var/lib/lxc/<id>/rootfs`
(`pct unmount <id>` afterwards). Do not hard-code a storage path such as a ZFS subvol: where the
volume lives depends on the storage, so take it from `pct config <id>` if you need it.

## Checklist

1. **MAC (`net0` hwaddr).** `pct restore` keeps the source's hwaddr. `--hostname` and `--onboot`
   given to `pct restore` do take effect; the MAC is the one field that silently does not change.
   Restore with `pct restore <id> <archive> --unique 1`, which assigns a random MAC, or set a fresh
   one before the first start with `pct set <id> --net0 name=eth0,bridge=vmbr0,hwaddr=<new>,...`
   (keep the other `net0` fields). Read it back: `pct config <id> | grep ^net0`. A duplicate MAC on
   one L2 breaks DHCP for both guests, and only from the moment the copy first starts.
2. **machine-id.** Blank `<rootfs>/etc/machine-id` (an empty file; systemd generates a new id at
   boot) and delete `<rootfs>/var/lib/dbus/machine-id`. For the other identities a clone shares,
   see `bitranox:net-tailscale`.
3. **SSH host keys.** Delete `<rootfs>/etc/ssh/ssh_host_*` and regenerate with
   `ssh-keygen -A -f <rootfs>`. On an unprivileged CT, chown the new files to the idmap base
   (`100000:100000` by default) afterwards, because they were created as host root. Inherited keys
   make the two machines indistinguishable to their clients.
4. **Hostname, DNS and description.** `pct set <id> --hostname <name>` (and check
   `<rootfs>/etc/hostname`), `--nameserver`/`--searchdomain` if the CT is to resolve differently
   from the source, and `--description`: the description is inherited verbatim and describes the
   SOURCE, so it actively misleads the next reader.
5. **The deploy checkout and every unit naming it.** A service may RUN from the source machine's
   checkout: a unit whose `WorkingDirectory=` or `ExecStart=` points there makes the copy run the
   other machine's code, and possibly push to its repo. Grep the units for the source's name and
   paths (`grep -rn <source-name> <rootfs>/etc/systemd/system <rootfs>/usr/lib/systemd/system`)
   and repoint them; do not just delete the directory.
6. **The application's own site data.** Registrations, presets and any address the service
   advertises. Blank an address rather than keep the source's, so a premature start fails loudly
   instead of answering for the machine still serving that site.

Archive everything you remove into a dated tar inside the guest rather than deleting it, so a
wrong call about whose data it was costs one restore.

## Verify from ground truth

Check the result itself, never the script that produced it: after the first start, compare the SSH
host key fingerprints (`ssh-keygen -lf <key>.pub`) with the source's and require them to differ,
read `net0`, `/etc/machine-id` and the hostname back, and on an unprivileged CT check that every
file you created from the host is owned by the idmap base (`stat -c '%u:%g' <file>`).
