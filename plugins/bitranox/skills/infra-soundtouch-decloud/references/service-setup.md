# Standing the service up, and finding the speakers

The replacement is **AfterTouch** (`github.com/gesellix/bose-soundtouch`). It plays the part the
Bose cloud used to: it serves the account and its presets, publishes the list of source types, and
provides the playback adapter that internet radio runs through.

## Phase 2: where it runs, and pinning the address

Ask the owner where it will run. It needs Docker, and it must sit on the SAME network as the
speakers. A NAS, a Raspberry Pi, a small home server or an always-on PC all work.

**Then pin that machine's address, and say why.** Each speaker stores the service address in its own
configuration. If the address later changes, every speaker breaks at once, long after the change,
and nothing points at the cause. Either give the machine a static address, or reserve its address on
the router by its MAC. Ask the owner which they can do; if neither, stop here, because the rest of
the procedure will come undone.

Routers differ too much to give steps for each. Tell the owner the reservation is usually under
DHCP, LAN or Connected Devices in the router's web interface, and that it works by MAC address. To
read the machine's own MAC and current address:

```bash
ip addr            # Linux: look for "link/ether" and "inet"
ipconfig /all      # Windows
ifconfig           # macOS
```

If they cannot find it, the router's client list shows the same MAC beside the machine's name.

## Phase 3: Docker

Check first, and only offer to install if it is missing:

```bash
docker --version && docker compose version
```

If that fails, ask which system the machine runs and walk them through it:

| System                | What to tell them                                                        |
|-----------------------|---------------------------------------------------------------------------|
| Windows or macOS      | Install Docker Desktop from docker.com, then start it and re-run the check |
| Ubuntu, Debian, Raspberry Pi OS | `curl -fsSL https://get.docker.com | sh`, then `sudo usermod -aG docker $USER` and log out and back in |
| Fedora, RHEL          | `sudo dnf install docker docker-compose-plugin` then `sudo systemctl enable --now docker` |
| Synology, QNAP        | Install the Container Manager or Container Station package from the vendor's package centre |

Re-run the check afterwards and confirm both commands answer before continuing. On Linux, if
`docker` needs `sudo` after installing, the group change has not taken effect yet: they must log out
and back in.

## Phase 4: the container

```yaml
services:
  soundtouch-service:
    image: ghcr.io/gesellix/bose-soundtouch:${SOUNDTOUCH_VERSION:-latest}
    container_name: soundtouch-service
    restart: unless-stopped
    network_mode: host
    environment:
      PORT: 8000
      HTTPS_PORT: 8443
      DATA_DIR: /app/data
      SERVER_URL: http://${SOUNDTOUCH_HOSTNAME}:8000
      HTTPS_SERVER_URL: https://${SOUNDTOUCH_HOSTNAME}:8443
      RECORD_INTERACTIONS: "true"
      DISCOVERY_INTERVAL: 5m
    volumes:
      - /opt/soundtouch/data:/app/data
```

`SOUNDTOUCH_HOSTNAME` is the pinned address from phase 2, for example `192.0.2.10`. Keep it in an
env file beside the compose file so changing it later needs no edit to the compose file itself.

**`network_mode: host` is mandatory and is the single most common way this setup fails.** Discovery
happens over SSDP and mDNS, which are multicast, and Docker's bridge network does not forward
multicast into a container. On a bridge the service starts, answers HTTP and finds no speakers at
all, so it looks correctly installed and is useless.

**Never add a `ports:` block.** It is invalid together with host networking and Docker only warns,
so a leftover block reads as though it applies and does nothing.

**`SERVER_URL` must not be `localhost` or `127.0.0.1`.** It is the address the SPEAKERS are told to
call back to. Pointing it at loopback tells every speaker to call itself.

Start it and confirm it answers:

Put both files in a directory of the owner's choosing. Any path works; `/opt/soundtouch` is only a
convention. Create it first, and create the compose file with whatever editor they are comfortable
with, or by pasting into a heredoc:

```bash
mkdir -p /opt/soundtouch/data && cd /opt/soundtouch
cat > docker-compose.yml <<'EOF'
... paste the compose file here ...
EOF
```

Then start it and confirm it answers:

```bash
docker compose up -d
curl -s -o /dev/null -w '%{http_code}\n' http://<service-host>:8000/
```

A `200` means the service is up. If `docker compose` reports a permission error on Linux, the owner
is not yet in the `docker` group: either log out and back in, or use `sudo docker compose` for now.
Do not leave them guessing which.

The admin interface is at `http://<service-host>:8000/admin`, and its health tab is the first place
to look when something is wrong later, not the last.

## Phase 5: finding the speakers

The service discovers them by itself. Check what it found:

```bash
curl -s http://<service-host>:8000/api/setup/devices
```

Each speaker's `device_id` is its Ethernet MAC in upper case with no separators.

**If a speaker is missing, it is usually not broken.** In order:

1. Ask the owner to press a button on the speaker, or start something playing on it. A speaker
   idling in power-save answers when it is polled, and pressing a button is the simplest way to make
   that happen. This is harmless and resolves most cases.
2. Confirm the speaker is on the same network as the service, not a guest network and not a
   different subnet. Multicast does not cross subnets, so a speaker on the other side of a router is
   invisible to discovery even though it is perfectly healthy.
3. Check from a machine on the same network segment as the speaker. A machine that cannot see it
   proves nothing about the speaker until you know that machine can see the rest of the network.

A speaker that has not been seen recently also has no entry in the router's address table. That is
not evidence it is unreachable, only that it has not spoken lately.
