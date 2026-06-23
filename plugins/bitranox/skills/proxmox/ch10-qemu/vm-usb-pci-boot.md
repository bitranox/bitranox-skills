# VM USB, Audio, PCI Passthrough and Boot Options

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 10.2.10 USB Passthrough


There are two different types of USB passthrough devices:

- Host USB passthrough
- SPICE USB passthrough
Host USB passthrough works by giving a VM a USB device of the host. This can either be done via the
vendor- and product-id, or via the host bus and port.
The vendor/product-id looks like this: 0123:abcd, where 0123 is the id of the vendor, and abcd is the id of
the product, meaning two pieces of the same usb device have the same id.
The bus/port looks like this: 1-2.3.4, where 1 is the bus and 2.3.4 is the port path. This represents the
physical ports of your host (depending of the internal order of the usb controllers).
If a device is present in a VM configuration when the VM starts up, but the device is not present in the host,
the VM can boot without problems. As soon as the device/port is available in the host, it gets passed through.


> **Warning:**
> Using this kind of USB passthrough means that you cannot move a VM online to another host, since
> the hardware is only available on the host the VM is currently residing.


The second type of passthrough is SPICE USB passthrough. If you add one or more SPICE USB ports to
your VM, you can dynamically pass a local USB device from your SPICE client through to the VM. This can
be useful to redirect an input device or hardware dongle temporarily.
It is also possible to map devices on a cluster level, so that they can be properly used with HA and hardware
changes are detected and non root users can configure them. See Resource Mapping for details on that.


### 10.2.11 BIOS and UEFI


In order to properly emulate a computer, QEMU needs to use a firmware. Which, on common PCs often
known as BIOS or (U)EFI, is executed as one of the first steps when booting a VM. It is responsible for doing
basic hardware initialization and for providing an interface to the firmware and hardware for the operating
system. By default QEMU uses SeaBIOS for this, which is an open-source, x86 BIOS implementation.
SeaBIOS is a good choice for most standard setups.
Some operating systems (such as Windows 11) may require use of an UEFI compatible implementation. In
such cases, you must use OVMF instead, which is an open-source UEFI implementation. 10
10 See the OVMF Project https://github.com/tianocore/tianocore.github.io/wiki/OVMF


There are other scenarios in which the SeaBIOS may not be the ideal firmware to boot from, for example if
you want to do VGA passthrough. 11
If you want to use OVMF, there are several things to consider:
In order to save things like the boot order, there needs to be an EFI Disk. This disk will be included in
backups and snapshots, and there can only be one.
You can create such a disk with the following command:


```
# qm set <vmid> -efidisk0 <storage>:1,format=<format>,efitype=4m,pre- ←enrolled-keys=1
Where <storage> is the storage where you want to have the disk, and <format> is a format which the
storage supports. Alternatively, you can create such a disk through the web interface with Add → EFI Disk
in the hardware section of a VM.
The efitype option specifies which version of the OVMF firmware should be used. For new VMs, this should
always be 4m, as it supports Secure Boot and has more space allocated to support future development (this
is the default in the GUI).
pre-enroll-keys specifies if the efidisk should come pre-loaded with distribution-specific and Microsoft Standard Secure Boot keys. It also enables Secure Boot by default (though it can still be disabled in the OVMF
menu within the VM).
Note
If you want to start using Secure Boot in an existing VM (that still uses a 2m efidisk), you need to recreate
the efidisk. To do so, delete the old one (qm set <vmid> -delete efidisk0) and add a new
one as described above. This will reset any custom configurations you have made in the OVMF menu!
```


When using OVMF with a virtual display (without VGA passthrough), you need to set the client resolution in
the OVMF menu (which you can reach with a press of the ESC button during boot), or you have to choose
SPICE as the display type.
When using OVMF with PXE boot, you have to add an RNG device to the VM. For security reasons, the
OVMF firmware disables PXE boot for guests without a random number generator.


### 10.2.12 Trusted Platform Module (TPM)


A Trusted Platform Module is a device which stores secret data - such as encryption keys - securely and
provides tamper-resistance functions for validating system boot.
Certain operating systems (such as Windows 11) require such a device to be attached to a machine (be it
physical or virtual).
A TPM is added by specifying a tpmstate volume. This works similar to an efidisk, in that it cannot be
changed (only removed) once created. You can add one via the following command:


```
# qm set <vmid> -tpmstate0 <storage>:1,version=<version>
11 Alex Williamson has a good blog entry about this https://vfio.blogspot.co.at/2014/08/primary-graphics-assignment-without-
```


vga.html


Where <storage> is the storage you want to put the state on, and <version> is either v1.2 or v2.0. You can
also add one via the web interface, by choosing Add → TPM State in the hardware section of a VM.
The v2.0 TPM spec is newer and better supported, so unless you have a specific implementation that
requires a v1.2 TPM, it should be preferred.

> **Note:**
> Compared to a physical TPM, an emulated one does not provide any real security benefits. The point of
> a TPM is that the data on it cannot be modified easily, except via commands specified as part of the TPM
> spec. Since with an emulated device the data storage happens on a regular volume, it can potentially be
> edited by anyone with access to it.


### 10.2.13 Inter-VM shared memory


You can add an Inter-VM shared memory device (ivshmem), which allows one to share memory between
the host and a guest, or also between multiple guests.
To add such a device, you can use qm:


```
# qm set <vmid> -ivshmem size=32,name=foo
Where the size is in MiB. The file will be located under /dev/shm/pve-shm-$name (the default name
is the vmid).
Note
Currently the device will get deleted as soon as any VM using it got shutdown or stopped. Open connections will still persist, but new connections to the exact same device cannot be made anymore.
```


A use case for such a device is the Looking Glass 12 project, which enables high performance, low-latency
display mirroring between host and guest.


### 10.2.14 Audio Device


To add an audio device run the following command:


```
qm set <vmid> -audio0 device=<device>
```

Supported audio devices are:

- ich9-intel-hda: Intel HD Audio Controller, emulates ICH9
- intel-hda: Intel HD Audio Controller, emulates ICH6
- AC97: Audio Codec ’97, useful for older operating systems like Windows XP
There are two backends available:
12 Looking Glass: https://looking-glass.io/


- spice
- none
The spice backend can be used in combination with SPICE while the none backend can be useful if an audio
device is needed in the VM for some software to work. To use the physical audio device of the host use
device passthrough (see PCI Passthrough and USB Passthrough). Remote protocols like Microsoft’s RDP
have options to play sound.


### 10.2.15 VirtIO RNG


A RNG (Random Number Generator) is a device providing entropy (randomness) to a system. A virtual
hardware-RNG can be used to provide such entropy from the host system to a guest VM. This helps to avoid
entropy starvation problems in the guest (a situation where not enough entropy is available and the system
may slow down or run into problems), especially during the guests boot process.
To add a VirtIO-based emulated RNG, run the following command:


```
qm set <vmid> -rng0 source=<source>[,max_bytes=X,period=Y]
```


source specifies where entropy is read from on the host and has to be one of the following:
- /dev/urandom: Non-blocking kernel entropy pool (preferred)
- /dev/random: Blocking kernel pool (not recommended, can lead to entropy starvation on the host
system)

- /dev/hwrng: To pass through a hardware RNG attached to the host (if multiple are available, the one
selected in /sys/devices/virtual/misc/hw_random/rng_current will be used)
A limit can be specified via the max_bytes and period parameters, they are read as max_bytes per
period in milliseconds. However, it does not represent a linear relationship: 1024B/1000ms would mean
that up to 1 KiB of data becomes available on a 1 second timer, not that 1 KiB is streamed to the guest over
the course of one second. Reducing the period can thus be used to inject entropy into the guest at a
faster rate.
By default, the limit is set to 1024 bytes per 1000 ms (1 KiB/s). It is recommended to always use a limiter to
avoid guests using too many host resources. If desired, a value of 0 for max_bytes can be used to disable
all limits.


### 10.2.16 Virtiofs


Virtiofs is a shared filesystem designed for virtual environments. It allows to share a directory tree available
on the host by mounting it within VMs. It does not use the network stack and aims to offer similar performance
and semantics as the source filesystem.
To use virtiofs, the virtiofsd daemon needs to run in the background. This happens automatically in Proxmox
VE when starting a VM using a virtiofs mount.
Linux VMs with kernel >=5.4 support virtiofs by default (virtiofs kernel module), but some features require a
newer kernel.
To use virtiofs, ensure that virtiofsd is installed on the Proxmox VE host:

apt install virtiofsd
There is a guide available on how to utilize virtiofs in Windows VMs.


Known Limitations

- If virtiofsd crashes, its mount point will hang in the VM until the VM is completely stopped.
- virtiofsd not responding may result in a hanging mount in the VM, similar to an unreachable NFS.
- Memory hotplug does not work in combination with virtiofs (also results in hanging access).
- Memory related features such as live migration, snapshots, and hibernate are not available with virtiofs
devices.

- Windows cannot understand ACLs in the context of virtiofs. Therefore, do not expose ACLs for Windows
VMs, otherwise the virtiofs device will not be visible within the VM.
Add Mapping for Shared Directories
To add a mapping for a shared directory, you can use the API directly with pvesh as described in the
Resource Mapping section:


```
pvesh create /cluster/mapping/dir --id dir1 \
```

- `--map` node=node1,path=/path/to/share1 \
- `--map` node=node2,path=/path/to/share2 \

Add virtiofs to a VM
To share a directory using virtiofs, add the parameter virtiofs<N> (N can be anything between 0 and 9)
to the VM config and use a directory ID (dirid) that has been configured in the resource mapping. Additionally,
you can set the cache option to either always, never, metadata, or auto (default: auto), depending
on your requirements. How the different caching modes behave can be read here under the "Caching Modes"
section.

The virtiofsd supports ACL and xattr passthrough (can be enabled with the expose-acl and expose-xat
options), allowing the guest to access ACLs and xattrs if the underlying host filesystem supports them, but
they must also be compatible with the guest filesystem (for example most Linux filesystems support ACLs,
while Windows filesystems do not).
The expose-acl option automatically implies expose-xattr, that is, it makes no difference if you set
expose-xattr to 0 if expose-acl is set to 1.
If you want virtiofs to honor the O_DIRECT flag, you can set the direct-io parameter to 1 (default: 0).
This will degrade performance, but is useful if applications do their own caching.


```
qm set <vmid> -virtiofs0 dirid=<dirid>,cache=always,direct-io=1
```


```
qm set <vmid> -virtiofs1 <dirid>,cache=never,expose-xattr=1
```


```
qm set <vmid> -virtiofs2 <dirid>,expose-acl=1
```

To temporarily mount virtiofs in a guest VM with the Linux kernel virtiofs driver, run the following command
inside the guest:

mount -t virtiofs <dirid> <mount point>
To have a persistent virtiofs mount, you can create an fstab entry:

<dirid> <mount point> virtiofs rw,relatime 0 0


The dirid associated with the path on the current node is also used as the mount tag (name used to mount
the device on the guest).
For more information on available virtiofsd parameters, see the GitLab virtiofsd project page.


### 10.2.17 Device Boot Order


QEMU can tell the guest which devices it should boot from, and in which order. This can be specified in the
config via the boot property, for example:

boot: order=scsi0;net0;hostpci0

This way, the guest would first attempt to boot from the disk scsi0, if that fails, it would go on to attempt
network boot from net0, and in case that fails too, finally attempt to boot from a passed through PCIe device
(seen as disk in case of NVMe, otherwise tries to launch into an option ROM).
On the GUI you can use a drag-and-drop editor to specify the boot order, and use the checkbox to enable or
disable certain devices for booting altogether.

> **Note:**
> If your guest uses multiple disks to boot the OS or load the bootloader, all of them must be marked as
> bootable (that is, they must have the checkbox enabled or appear in the list in the config) for the guest
> to be able to boot. This is because recent SeaBIOS and OVMF versions only initialize disks if they are
> marked bootable.


In any case, even devices not appearing in the list or having the checkmark disabled will still be available
to the guest, once it’s operating system has booted and initialized them. The bootable flag only affects the
guest BIOS and bootloader.


### 10.2.18 Automatic Start and Shutdown of Virtual Machines


After creating your VMs, you probably want them to start automatically when the host system boots. For this
you need to select the option Start at boot from the Options Tab of your VM in the web interface, or set it
with the following command:


```
# qm set <vmid> -onboot 1
```


## See also

- [VM Settings: Hardware](vm-settings-hardware.md)
- [VM CPU and Memory Settings](vm-cpu-memory.md)
- [VM Memory Encryption and Display](vm-memory-encryption-display.md)
- [QEMU/KVM Overview](_index.md)
