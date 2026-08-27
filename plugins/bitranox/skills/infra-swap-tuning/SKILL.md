---
name: infra-swap-tuning
description: Use when deciding a Linux host's swap configuration - whether to add zram compressed swap, what size, what swap priority, and what vm.swappiness to set - or when a host froze with the kernel still alive (ping answers, cluster membership holds, TCP connects succeed) while sshd never completes a banner and every container userland is stuck, especially with swap on a ZFS zvol. Covers measuring compressibility and pressure before choosing numbers rather than applying a general recommendation.
---

# infra-swap-tuning

## Overview

Swap tuning advice is written for general-purpose servers. On a hypervisor the anonymous memory
is mostly GUEST RAM, which breaks the assumption every recommendation rests on. Measure the two
inputs that decide the numbers, then set them.

**Core principle: the compression ratio of the memory that would actually be swapped decides
whether swapping is cheap. Measure it. Do not assume it.**

## The freeze this prevents

Swap on a ZFS zvol is a deadlock: under pressure the kernel must page out, paging out re-enters
ZFS, and ZFS needs memory to finish. The result is not an OOM kill but a total userland stall.

Recognise it by what still WORKS:

| Still alive                             | Frozen                                   |
|-----------------------------------------|------------------------------------------|
| ICMP (answered in softirq)              | sshd - accepts TCP, never sends a banner |
| corosync / cluster membership (RT prio) | every container's userland               |
| TCP connect (kernel accept queue)       | all VMs                                  |
| the kernel                              | anything needing an allocation or fork   |

A container answering ping proves nothing: for a veth guest the HOST kernel replies. Test guest
userland with a real ssh login, not ICMP.

**The local journal will be empty.** journald writes through the same stalled path, so it stops
mid-operation with nothing logged. Look for network-shipped logs instead (rsyslog to a remote
collector leaves the box before the stall), and check the pool and cumulative pressure after the
reboot:

```bash
journalctl -b -1 -p warning | grep -iE 'oom|hung_task|blocked for more than|nvme|txg'
cat /proc/pressure/memory        # total= counters are cumulative since boot, avg* are now
zpool status -x; swapon --show
```

## Measure before choosing

### 1. Is the host actually swapping, and under pressure?

```bash
swapon --show                    # USED per device, and the PRIO ordering
awk '/^SwapTotal|^SwapFree/' /proc/meminfo
cat /proc/pressure/memory        # some/full avg10 near 0 = not constrained right now
```

Nodes that already swap several GB at `swappiness=10` will use zram without any swappiness
change, because pressure-driven reclaim ignores swappiness and picks the highest priority device.

### 2. How well does the memory that would be swapped compress?

This is the input almost everyone skips, and it is the one that decides swappiness. Sample real
anonymous memory from the largest process and compress it:

```bash
PID=$(ps -eo pid,rss,comm --sort=-rss --no-headers | awk 'NR==1{print $1}')
python3 - "$PID" <<'PY'
import subprocess, sys
pid = sys.argv[1]; out = bytearray()
for line in open(f"/proc/{pid}/maps"):
    f = line.split()
    if "w" not in f[1] or (len(f) > 5 and f[5].startswith("/")):
        continue
    lo, _, hi = f[0].partition("-"); start, end = int(lo, 16), int(hi, 16)
    if end - start < 64 << 20:
        continue
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as m:
        pos, stride = start, max(1 << 20, (end - start) // 64)
        while pos + (1 << 20) <= end and len(out) < 24 << 20:
            try:
                m.seek(pos); out += m.read(1 << 20)
            except OSError:
                pass
            pos += stride
    if len(out) >= 24 << 20:
        break
data = bytes(out); zeros = data.count(0) / len(data) * 100
comp = subprocess.run(["zstd", "-3", "-c", "-"], input=data, capture_output=True).stdout
print(f"{len(data) >> 20} MB  ratio {len(data)/len(comp):.2f}x  zero pages {zeros:.1f}%")
PY
```

**Discount the zero pages.** They are untouched memory, they compress to nothing, and they
inflate the headline ratio. A 1.67x reading with 30% zeros is about 1.16x on the real working
set - which is what a hypervisor typically measures, because guest RAM looks close to random.

## Decide from the measurements

| Net ratio (zeros discounted)      | Set swappiness | Why                                        |
|-----------------------------------|----------------|--------------------------------------------|
| below 1.3x - the hypervisor case  | leave at 10    | swapping buys ~20% and costs guest latency |
| 1.3x to 2x                        | leave at 10    | too little gain to justify the churn       |
| above 2x - general-purpose server | 60 to 100      | swapping is genuinely cheap; usual advice  |

Two other readings and what they mean:

- **Already swapping GB at swappiness 10** - zram will be used without any swappiness change.
- **`full avg10` above 0 outside a stress test** - a capacity problem, not a tuning problem. No
  swappiness value fixes an oversubscribed host; reduce commitment.

**Do not go below 10 either.** Near 0 the kernel discards page cache rather than swap anything,
trading one kind of thrash for another.

### What swappiness does and does not control

These two statements look contradictory and are not:

- Under GENUINE pressure the kernel swaps regardless of swappiness and picks the highest-priority
  device. That is why zram removes the deadlock **at any swappiness**, and why the ratio never
  gates the decision to add it.
- swappiness governs how eagerly reclaim trades anonymous pages for page cache BEFORE pressure
  turns acute - the routine, proactive swapping.

So the measurement decides how much ROUTINE swapping you want, not whether the safety valve
works. On a hypervisor that routine traffic is guest RAM at ~1.16x, so you want little of it.

**Add zram regardless of the ratio if swap lives on a zvol.** Its job there is to keep swap
traffic off the deadlock path, and that works at any swappiness.

```ini
# /etc/systemd/zram-generator.conf
[zram0]
zram-size = 16384             # MB, uncompressed capacity; about 25% of RAM
compression-algorithm = zstd
swap-priority = 100           # above the disk device, so zram fills first
fs-type = swap
```

**Keep the disk swap as a lower-priority backstop.** It is the real capacity; zram is not. Pages
parked on disk are cold pages costing nothing - pulling them into RAM at 1.16x would consume
roughly the memory their eviction freed.

**`zram-size` is a cap, not a reservation.** It costs only what actually lands in it. Size it by
what you are willing to lose to a full device, not by what looks generous: at ~1.16x a full
device is close to a 1:1 RAM sink.

## Verify from outside the deploy

A configuration-management run reports its own success, not the kernel's. Check the kernel:

```bash
swapon --show                          # zram present, and at the PRIO you set
cat /sys/block/zram0/comp_algorithm    # the selected algorithm is in [brackets]
awk '{print "orig",$1,"compressed",$2}' /sys/block/zram0/mm_stat
systemctl is-active dev-zram0.swap
```

## Automating it idempotently

Two traps, both of which produce a green run and a broken host:

- **Never restart `systemd-zram-setup@zram0` when the device is already swapping.** The restart
  tears the swap down, then the re-setup hits `EBUSY` because the device is still initialised,
  and the node ends with no zram at all.
- **Skip on the DESIRED STATE, not on liveness.** A guard that returns early whenever zram is
  active silently ignores a changed `zram-size`. Compare `/sys/block/zram0/disksize` against the
  configured value, but CONVERT FIRST: the kernel reports `disksize` in BYTES while
  `zram-generator.conf`'s `zram-size` is in MEGABYTES, so an 8192 device reads 8589934592.
  Compared raw they are never equal, which turns this guard into the unconditional
  swapoff/reset the bullet above warns against.

  ```bash
  want_mb=$(awk -F= '/^zram-size/ {gsub(/ /,"",$2); print $2}' /etc/systemd/zram-generator.conf)
  have_bytes=$(cat /sys/block/zram0/disksize)
  [ "$have_bytes" -eq "$(( want_mb * 1024 * 1024 ))" ] || need_reset=1
  ```

  `zram-size` also accepts expressions (`min(ram / 10, 2048)`); resolve one to a number before
  comparing, or the arithmetic above fails rather than reporting a difference.

If the host runs a module allowlist, `zram` and its compression backends must be whitelisted, and
that block is silent - see `bitranox:infra-modulejail`.

## Common mistakes

| Mistake                                        | Consequence                                              |
|------------------------------------------------|----------------------------------------------------------|
| Applying `swappiness=100` because zram is fast | Swaps incompressible guest RAM; CPU cost, VM latency     |
| Sizing zram as a memory multiplier             | At ~1.16x it is nearly a 1:1 RAM sink when full          |
| Removing the disk swap once zram exists        | Loses the real capacity; OOM arrives sooner              |
| Reading a container's ping as guest health     | The host kernel answers; guest userland can be frozen    |
| Trusting the local journal after a freeze      | journald stalled with everything else and logged nothing |
| Trusting a deploy's "ok" for zram              | Wrappers swallow hook output, warning included           |
