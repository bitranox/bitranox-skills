# Firmware Updates

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


> **Tip:**
> Regular updates are essential to get the latest patches and security related fixes. Major system upgrades
> are announced in the Proxmox VE Community Forum.


## 3.3 Firmware Updates


Firmware updates from this chapter should be applied when running Proxmox VE on a bare-metal server.
Whether configuring firmware updates is appropriate within guests, e.g. when using device pass-through,
depends strongly on your setup and is therefore out of scope.
In addition to regular software updates, firmware updates are also important for reliable and secure operation.
When obtaining and applying firmware updates, a combination of available options is recommended to get
them as early as possible or at all.
The term firmware is usually divided linguistically into microcode (for CPUs) and firmware (for other devices).


### 3.3.1 Persistent Firmware


This section is suitable for all devices. Updated microcode, which is usually included in a BIOS/UEFI update,
is stored on the motherboard, whereas other firmware is stored on the respective device. This persistent
method is especially important for the CPU, as it enables the earliest possible regular loading of the updated
microcode at boot time.

> **Caution:**
> With some updates, such as for BIOS/UEFI or storage controller, the device configuration could be
> reset. Please follow the vendor’s instructions carefully and back up the current configuration.


Please check with your vendor which update methods are available.

- Convenient update methods for servers can include Dell’s Lifecycle Manager or Service Packs from HPE.
- Sometimes there are Linux utilities available as well. Examples are mlxup for NVIDIA ConnectX or
bnxtnvm/niccli for Broadcom network cards.

- LVFS is also an option if there is a cooperation with the hardware vendor and supported hardware in use.
The technical requirement for this is that the system was manufactured after 2014 and is booted via UEFI.
Proxmox VE ships its own version of the fwupd package to enable Secure Boot Support with the Proxmox
signing key. This package consciously dropped the dependency recommendation for the udisks2 package, due to observed issues with its use on hypervisors. That means you must explicitly configure the correct
mount point of the EFI partition in /etc/fwupd/daemon.conf, for example:


File /etc/fwupd/daemon.conf

# Override the location used for the EFI system partition (ESP) path.
EspLocation=/boot/efi


> **Tip:**
> If the update instructions require a host reboot, make sure that it can be done safely. See also Node
> Maintenance.


### 3.3.2 Runtime Firmware Files


This method stores firmware on the Proxmox VE operating system and will pass it to a device if its persisted
firmware is less recent. It is supported by devices such as network and graphics cards, but not by those that
rely on persisted firmware such as the motherboard and hard disks.
In Proxmox VE the package pve-firmware is already installed by default. Therefore, with the normal
system updates (APT), included firmware of common hardware is automatically kept up to date.
An additional Debian Firmware Repository exists, but is not configured by default.
If you try to install an additional firmware package but it conflicts, APT will abort the installation. Perhaps the
particular firmware can be obtained in another way.


### 3.3.3 CPU Microcode Updates


Microcode updates are intended to fix found security vulnerabilities and other serious CPU bugs. While the
CPU performance can be affected, a patched microcode is usually still more performant than an unpatched
microcode where the kernel itself has to do mitigations. Depending on the CPU type, it is possible that
performance results of the flawed factory state can no longer be achieved without knowingly running the
CPU in an unsafe state.
To get an overview of present CPU vulnerabilities and their mitigations, run lscpu. Current real-world
known vulnerabilities can only show up if the Proxmox VE host is up to date, its version not end of life, and
has at least been rebooted since the last kernel update.
Besides the recommended microcode update via persistent BIOS/UEFI updates, there is also an independent method via Early OS Microcode Updates. It is convenient to use and also quite helpful when the
motherboard vendor no longer provides BIOS/UEFI updates. Regardless of the method in use, a reboot is
always needed to apply a microcode update.

Set up Early OS Microcode Updates
To set up microcode updates that are applied early on boot by the Linux kernel, you need to:
1. Enable the Debian Firmware Repository
2. Get the latest available packages apt update (or use the web interface, under Node → Updates)
3. Install the CPU-vendor specific microcode package:


- For Intel CPUs: apt install intel-microcode
- For AMD CPUs: apt install amd64-microcode
4. Reboot the Proxmox VE host
Any future microcode update will also require a reboot to be loaded.
Microcode Version
To get the current running microcode revision for comparison or debugging purposes:


```
# grep microcode /proc/cpuinfo | uniq
microcode
: 0xf0
A microcode package has updates for many different CPUs. But updates specifically for your CPU might not
come often. So, just looking at the date on the package won’t tell you when the company actually released
an update for your specific CPU.
If you’ve installed a new microcode package and rebooted your Proxmox VE host, and this new microcode
is newer than both, the version baked into the CPU and the one from the motherboard’s firmware, you’ll see
a message in the system log saying "microcode updated early".

# dmesg | grep microcode
[
0.000000] microcode: microcode updated early to revision 0xf0, date =
2021-11-12
[
0.896580] microcode: Microcode Update Driver: v2.2.
```


←-

Troubleshooting
For debugging purposes, the set up Early OS Microcode Update applied regularly at system boot can be
temporarily disabled as follows:
1. make sure that the host can be rebooted safely
2. reboot the host to get to the GRUB menu (hold SHIFT if it is hidden)
3. at the desired Proxmox VE boot entry press E
4. go to the line which starts with linux and append separated by a space dis_ucode_ldr
5. press CTRL-X to boot this time without an Early OS Microcode Update
If a problem related to a recent microcode update is suspected, a package downgrade should be considered
instead of package removal (apt purge <intel-microcode|amd64-microcode>). Otherwise,
a too old persisted microcode might be loaded, even though a more recent one would run without problems.
A downgrade is possible if an earlier microcode package version is available in the Debian repository, as
shown in this example:


```
# apt list -a intel-microcode
Listing... Done
intel-microcode/stable-security,now 3.20230808.1~deb12u1 amd64 [installed]
intel-microcode/stable 3.20230512.1 amd64
```


```
# apt install intel-microcode=3.202305*
...
Selected version '3.20230512.1' (Debian:12.1/stable [amd64]) for 'intel- ←microcode'
...
dpkg: warning: downgrading intel-microcode from 3.20230808.1~deb12u1 to ←3.20230512.1
...
intel-microcode: microcode will be updated at next boot
...
Make sure (again) that the host can be rebooted safely. To apply an older microcode potentially included in
the microcode package for your CPU type, reboot now.
Tip
It makes sense to hold the downgraded package for a while and try more recent versions again at a
later time. Even if the package version is the same in the future, system updates may have fixed the
experienced problem in the meantime.

# apt-mark hold intel-microcode
intel-microcode set on hold.
# apt-mark unhold intel-microcode
# apt update
# apt full-upgrade
```


## 3.4 Network Configuration


Proxmox VE is using the Linux network stack. This provides a lot of flexibility on how to set up the network
on the Proxmox VE nodes. The configuration can be done either via the GUI, or by manually editing the file
/etc/network/interfaces, which contains the whole network configuration. The interfaces(5)
manual page contains the complete format description. All Proxmox VE tools try hard to keep direct user
modifications, but using the GUI is still preferable, because it protects you from errors.
A Linux bridge interface (commonly called vmbrX ) is needed to connect guests to the underlying physical
network. It can be thought of as a virtual switch which the guests and physical interfaces are connected
to. This section provides some examples on how the network can be set up to accommodate different use
cases like redundancy with a bond, vlans or routed and NAT setups.
The Software Defined Network is an option for more complex virtual networks in Proxmox VE clusters.

> **Warning:**
> It’s discouraged to use the traditional Debian tools ifup and ifdown if unsure, as they have some
> pitfalls like interrupting all guest traffic on ifdown vmbrX but not reconnecting those guest again
> when doing ifup on the same bridge later.

