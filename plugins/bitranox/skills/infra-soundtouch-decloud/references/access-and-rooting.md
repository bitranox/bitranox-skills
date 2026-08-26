# Getting access to a speaker

Two ways in, and they are not equivalent.

**Port 17000 is the diagnostic port.** It is open on a stock speaker, needs no credentials, and
speaks a small command language ending each reply with a `->` prompt. Everything the migration needs
can be done here. Most owners never need more than this.

**Port 22 is SSH, and is closed on a stock speaker.** It is only needed for the service endpoints
that act on the speaker directly, such as rebooting it through the service. Opening it is called
rooting, and it is optional. Do not root a speaker to satisfy a checklist.

Ask before opening SSH, and say why it is wanted. If the owner would rather not, say so plainly:
the migration works over the diagnostic port alone.

## Check what is already open

```bash
uv run scripts/soundtouch_find.py --ip <speaker-ip>
```

Never probe a port with the `echo > /dev/tcp/host/port` shell redirect. It is a bash builtin, and
under `sh` (which is dash on Debian and Ubuntu, and is what `docker exec` and `ssh host 'cmd'` often
give you) it fails for every port, so a wide-open port reports as closed and nothing says why.

## Opening SSH, by firmware

| Firmware        | Method that works                                             |
|-----------------|----------------------------------------------------------------|
| Before 26.x     | `remote_services on` over port 17000                           |
| 26.x and later  | That command is rejected; use the USB stick                    |
| 27.x            | USB stick; the injection below only if no stick can be plugged in |
| Will not boot   | Boot from a prepared stick, for recovery                       |

### The USB stick, preferred

A FAT-formatted stick with an EMPTY file named `remote_services` (no extension) in its root. Plug it
into the speaker's USB port. The speaker's mount script sees the file and enables SSH and telnet
immediately, with no reboot. The stick can be removed afterwards.

Ask the owner whether they can plug a stick in. It is the safest method by a wide margin, and it is
the one to offer first. On macOS the hidden metadata has to be removed first or the speaker ignores
the file:

```bash
mdutil -i off /Volumes/USB && rm -rf /Volumes/USB/.fseventsd /Volumes/USB/.Spotlight-V100
```

Some speakers only accept the stick while on Ethernet rather than WiFi.

### The injection, last resort on 27.x

On firmware 27.x with no way to reach the USB port, SSH can be opened by appending shell text to the
account URL, which this firmware passes to a shell. It is more invasive than the stick because it
puts shell text into a live configuration value, so it needs the owner's agreement and it must be
cleaned up in the same sitting.

Send over port 17000, in this order:

```
sys configuration margeServerUrl "http://<service-host>:8000;touch /tmp/remote_services;/etc/init.d/sshd start"
sys configuration bmxRegistryUrl "http://<service-host>:8000/bmx/registry/v1/services"
sys configuration statsServerUrl "http://<service-host>:8000"
sys configuration swUpdateUrl    "http://<service-host>:8000/updates/soundtouch"
envswitch boseurls set "http://<service-host>:8000;touch /tmp/remote_services;/etc/init.d/sshd start" "http://<service-host>:8000/updates/soundtouch"
sys reboot
```

Two follow-ups are mandatory, not optional:

1. Rewrite all four URLs WITHOUT the appended text (see migration.md), or the account URL keeps
   shell commands in it permanently.
2. Write the flash marker below, or SSH is gone at the next reboot.

## The flash marker, without which nothing sticks

Both the stick and the injection only leave the marker in `/tmp`, which is cleared on every boot. On
the speaker itself:

```sh
touch /mnt/nv/remote_services
```

`/mnt/nv` is a separate flash volume that survives reboots. Skipping this fails SILENTLY: everything
works until the next power cut, and then the speaker looks as though the whole procedure never
happened.

Prove it took, by rebooting and checking that the `/tmp` marker is gone while the flash one remains:

```sh
for f in /mnt/nv/remote_services /etc/remote_services /tmp/remote_services; do
    [ -e "$f" ] && echo "YES $f" || echo "no  $f"
done
```

Only `/tmp` present means access disappears at the next boot.

## Logging in

The firmware only offers old host key algorithms, so a current SSH client refuses it by default:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa root@<speaker-ip>
```

User `root`, no password. Tell the owner this plainly: the speaker has no password and anyone on
their network can log into it once SSH is open. That is a reason to leave SSH closed unless it is
needed.

A factory reset does NOT close it again. Reset clears the account, the presets, the four URLs and
the name, but the flash marker, SSH and telnet all survive.
