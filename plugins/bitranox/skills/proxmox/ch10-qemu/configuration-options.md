# VM Configuration Options

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

type=<sev-type>
Enable standard SEV with type=std or enable experimental SEV-ES with the es option or enable
experimental SEV-SNP with the snp option.

arch: <aarch64 | x86_64>
Virtual processor architecture. Defaults to the host.

args: <string>
Arbitrary arguments passed to kvm, for example:
args: -no-reboot -smbios type=0,vendor=FOO

> **Note:**
> this option is for experts only.


audio0: device=<ich9-intel-hda|intel-hda|AC97>
[,driver=<spice|none>]
Configure a audio device, useful in combination with QXL/Spice.

device=<AC97 | ich9-intel-hda | intel-hda>
Configure an audio device.

driver=<none | spice> (default = spice)
Driver backend for the audio device.

autostart: <boolean> (default = 0)
Automatic restart after crash (currently ignored).

balloon: <integer> (0 - N)
Amount of target RAM for the VM in MiB. Using zero disables the ballon driver.

bios: <ovmf | seabios> (default = seabios)
Select BIOS implementation.

boot: [[legacy=]<[acdn]{1,4}>] [,order=<device[;device...]>]
Specify guest boot order. Use the order= sub-property as usage with no key or legacy= is deprecated.

legacy=<[acdn]{1,4}> (default = cdn)
Boot on floppy (a), hard disk (c), CD-ROM (d), or network (n). Deprecated, use order= instead.

order=<device[;device...]>
The guest will attempt to boot from devices in the order they appear here.
Disks, optical drives and passed-through storage USB devices will be directly booted from, NICs
will load PXE, and PCIe devices will either behave like disks (e.g. NVMe) or load an option ROM
(e.g. RAID controller, hardware NIC).


Note that only devices in this list will be marked as bootable and thus loaded by the guest
firmware (BIOS/UEFI). If you require multiple disks for booting (e.g. software-raid), you need
to specify all of them here.
Overrides the deprecated legacy=[acdn]* value when given.

bootdisk: (ide|sata|scsi|virtio)\d+
Enable booting from specified disk. Deprecated: Use boot: order=foo;bar instead.

cdrom: <volume>
This is an alias for option -ide2

cicustom: [meta=<volume>] [,network=<volume>] [,user=<volume>]
[,vendor=<volume>]
cloud-init: Specify custom files to replace the automatically generated ones at start.

meta=<volume>
Specify a custom file containing all meta data passed to the VM via cloud-init. This is provider
specific meaning configdrive2 and nocloud differ.

network=<volume>
To pass a custom file containing all network data to the VM via cloud-init.

user=<volume>
To pass a custom file containing all user data to the VM via cloud-init.

vendor=<volume>
To pass a custom file containing all vendor data to the VM via cloud-init.

cipassword: <string>
cloud-init: Password to assign the user. Using this is generally not recommended. Use ssh keys
instead. Also note that older cloud-init versions do not support hashed passwords.

citype: <configdrive2 | nocloud | opennebula>
Specifies the cloud-init configuration format. The default depends on the configured operating system
type (ostype. We use the nocloud format for Linux, and configdrive2 for windows.

ciupgrade: <boolean> (default = 1)
cloud-init: do an automatic package upgrade after the first boot.

ciuser: <string>
cloud-init: User name to change ssh keys and password for instead of the image’s configured default
user.

cores: <integer> (1 - N) (default = 1)
The number of cores per socket.


cpu: [[cputype=]<string>] [,flags=<+FLAG[;-FLAG...]>]
[,guest-phys-bits=<integer>] [,hidden=<1|0>]
[,hv-vendor-id=<vendor-id>] [,phys-bits=<8-64|host>]
[,reported-model=<enum>]
Emulated CPU type.

cputype=<string> (default = kvm64)
Emulated CPU type. Can be default or custom name (custom model names must be prefixed
with custom-).

flags=<+FLAG[;-FLAG...]>
List of additional CPU flags separated by ;. Use +FLAG to enable, -FLAG to disable a flag. There
is a special nested-virt shorthand which controls nested virtualization for the current CPU (svm
for AMD and vmx for Intel). Custom CPU models can specify any flag supported by QEMU/KVM,
VM-specific flags must be from the following set for security reasons: nested-virt, md-clear, pcid,
spec-ctrl, ssbd, ibpb, virt-ssbd, amd-ssbd, amd-no-ssb, pdpe1gb, hv-tlbflush, hv-evmcs, aes

guest-phys-bits=<integer> (32 - 64)
Number of physical address bits available to the guest.

hidden=<boolean> (default = 0)
Do not identify as a KVM virtual machine.

hv-vendor-id=<vendor-id>
The Hyper-V vendor ID. Some drivers or programs inside Windows guests need a specific ID.

phys-bits=<8-64|host>
The physical memory address bits that are reported to the guest OS. Should be smaller or equal
to the host’s. Set to host to use value from host CPU, but note that doing so will break live
migration to CPUs with other values.


reported-model=<486 | Broadwell | Broadwell-IBRS |
Broadwell-noTSX | Broadwell-noTSX-IBRS | Cascadelake-Server |
Cascadelake-Server-noTSX | Cascadelake-Server-v2 |
Cascadelake-Server-v4 | Cascadelake-Server-v5 | Conroe |
Cooperlake | Cooperlake-v2 | EPYC | EPYC-Genoa | EPYC-IBPB |
EPYC-Milan | EPYC-Milan-v2 | EPYC-Rome | EPYC-Rome-v2 |
EPYC-Rome-v3 | EPYC-Rome-v4 | EPYC-v3 | EPYC-v4 | GraniteRapids
| Haswell | Haswell-IBRS | Haswell-noTSX | Haswell-noTSX-IBRS |
Icelake-Client | Icelake-Client-noTSX | Icelake-Server |
Icelake-Server-noTSX | Icelake-Server-v3 | Icelake-Server-v4 |
Icelake-Server-v5 | Icelake-Server-v6 | IvyBridge |
IvyBridge-IBRS | KnightsMill | Nehalem | Nehalem-IBRS |
Opteron_G1 | Opteron_G2 | Opteron_G3 | Opteron_G4 | Opteron_G5
| Penryn | SandyBridge | SandyBridge-IBRS | SapphireRapids |
SapphireRapids-v2 | Skylake-Client | Skylake-Client-IBRS |
Skylake-Client-noTSX-IBRS | Skylake-Client-v4 | Skylake-Server
| Skylake-Server-IBRS | Skylake-Server-noTSX-IBRS |
Skylake-Server-v4 | Skylake-Server-v5 | Westmere |
Westmere-IBRS | athlon | core2duo | coreduo | host | kvm32 |
kvm64 | max | pentium | pentium2 | pentium3 | phenom | qemu32 |
qemu64> (default = kvm64)
CPU model and vendor to report to the guest. Must be a QEMU/KVM supported model. Only
valid for custom CPU model definitions, default models will always report themselves to the guest
OS.

cpulimit: <number> (0 - 128) (default = 0)
Limit of CPU usage.

> **Note:**
> If the computer has 2 CPUs, it has total of 2 CPU time. Value 0 indicates no CPU limit.


cpuunits: <integer> (1 - 262144) (default = cgroup v1:
100)

1024, cgroup v2:

CPU weight for a VM. Argument is used in the kernel fair scheduler. The larger the number is, the
more CPU time this VM gets. Number is relative to weights of all the other running VMs.

description: <string>
Description for the VM. Shown in the web-interface VM’s summary. This is saved as comment inside
the configuration file.

efidisk0: [file=]<volume> [,efitype=<2m|4m>] [,format=<enum>]
[,ms-cert=<2011|2023>] [,pre-enrolled-keys=<1|0>]
[,size=<DiskSize>]
Configure a disk for storing EFI vars.


efitype=<2m | 4m> (default = 2m)
Size and type of the OVMF EFI vars. 4m is newer and recommended, and required for Secure
Boot. For backwards compatibility, 2m is used if not otherwise specified. Ignored for VMs with
arch=aarch64 (ARM).

file=<volume>
The drive’s backing volume.

format=<cloop | qcow | qcow2 | qed | raw | vmdk>
The drive’s backing file’s data format.

ms-cert=<2011 | 2023> (default = 2011)
Informational marker indicating the version of the latest Microsof UEFI certificate that has been
enrolled by Proxmox VE.

pre-enrolled-keys=<boolean> (default = 0)
Use am EFI vars template with distribution-specific and Microsoft Standard keys enrolled, if used
with efitype=4m. Note that this will enable Secure Boot by default, though it can still be turned off
from within the VM.

size=<DiskSize>
Disk size. This is purely informational and has no effect.

freeze: <boolean>
Freeze CPU at startup (use c monitor command to start execution).

hookscript: <string>
Script that will be executed during various steps in the vms lifetime.

hostpci[n]: [[host=]<HOSTPCIID[;HOSTPCIID2...]>] [,device-id=<hex
id>] [,driver=<vfio|keep>] [,legacy-igd=<1|0>]
[,mapping=<mapping-id>] [,mdev=<string>] [,pcie=<1|0>]
[,rombar=<1|0>] [,romfile=<string>] [,sub-device-id=<hex id>]
[,sub-vendor-id=<hex id>] [,vendor-id=<hex id>] [,x-vga=<1|0>]
Map host PCI devices into guest.

> **Note:**
> This option allows direct access to host hardware. So it is no longer possible to migrate such
> machines - use with special care.


> **Caution:**
> Experimental! User reported problems with this option.


device-id=<hex id>
Override PCI device ID visible to guest


driver=<keep | vfio> (default = vfio)
If set to keep the device will neither be reset nor bound to the vfio-pci driver. Useful for devices
that already have the correct driver loaded.

host=<HOSTPCIID[;HOSTPCIID2...]>
Host PCI device pass through. The PCI ID of a host’s PCI device or a list of PCI virtual functions
of the host. HOSTPCIID syntax is:
bus:dev.func (hexadecimal numbers)
You can use the lspci command to list existing PCI devices.
Either this or the mapping key must be set.

legacy-igd=<boolean> (default = 0)
Pass this device in legacy IGD mode, making it the primary and exclusive graphics device in the
VM. Requires pc-i440fx machine type and VGA set to none.

mapping=<mapping-id>
The ID of a cluster wide mapping. Either this or the default-key host must be set.

mdev=<string>
The type of mediated device to use. An instance of this type will be created on startup of the VM
and will be cleaned up when the VM stops.

pcie=<boolean> (default = 0)
Choose the PCI-express bus (needs the q35 machine model).

rombar=<boolean> (default = 1)
Specify whether or not the device’s ROM will be visible in the guest’s memory map.

romfile=<string>
Custom pci device rom filename (must be located in /usr/share/kvm/).

sub-device-id=<hex id>
Override PCI subsystem device ID visible to guest

sub-vendor-id=<hex id>
Override PCI subsystem vendor ID visible to guest

vendor-id=<hex id>
Override PCI vendor ID visible to guest

x-vga=<boolean> (default = 0)
Enable vfio-vga device support.

hotplug: <string> (default = network,disk,usb)
Selectively enable hotplug features. This is a comma separated list of hotplug features: network, disk,
cpu, memory, usb and cloudinit. Use 0 to disable hotplug completely. Using 1 as value is an alias for
the default network,disk,usb. USB hotplugging is possible for guests with machine version >=

## 7.1 and ostype l26 or windows > 7.


hugepages: <1024 | 2 | any>
Enables hugepages memory.


Sets the size of hugepages in MiB. If the value is set to any then 1 GiB hugepages will be used if
possible, otherwise the size will fall back to 2 MiB.

ide[n]: [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,iops=<iops>] [,iops_max=<iops>] [,iops_max_length=<seconds>]
[,iops_rd=<iops>] [,iops_rd_max=<iops>]
[,iops_rd_max_length=<seconds>] [,iops_wr=<iops>]
[,iops_wr_max=<iops>] [,iops_wr_max_length=<seconds>]
[,mbps=<mbps>] [,mbps_max=<mbps>] [,mbps_rd=<mbps>]
[,mbps_rd_max=<mbps>] [,mbps_wr=<mbps>] [,mbps_wr_max=<mbps>]
[,media=<cdrom|disk>] [,model=<model>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,serial=<serial>] [,shared=<1|0>]
[,size=<DiskSize>] [,snapshot=<1|0>] [,ssd=<1|0>] [,werror=<enum>]
[,wwn=<wwn>]
Use volume as IDE hard disk or CD-ROM (n is 0 to 3).

aio=<io_uring | native | threads>
AIO type to use.

backup=<boolean>
Whether the drive should be included when making backups.

bps=<bps>
Maximum r/w speed in bytes per second.

bps_max_length=<seconds>
Maximum length of I/O bursts in seconds.

bps_rd=<bps>
Maximum read speed in bytes per second.

bps_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

bps_wr=<bps>
Maximum write speed in bytes per second.

bps_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

cache=<directsync | none | unsafe | writeback | writethrough>
The drive’s cache mode

detect_zeroes=<boolean>
Controls whether to detect and try to optimize writes of zeroes.


discard=<ignore | on>
Controls whether to pass discard/trim requests to the underlying storage.

file=<volume>
The drive’s backing volume.

format=<cloop | qcow | qcow2 | qed | raw | vmdk>
The drive’s backing file’s data format.

iops=<iops>
Maximum r/w I/O in operations per second.

iops_max=<iops>
Maximum unthrottled r/w I/O pool in operations per second.

iops_max_length=<seconds>
Maximum length of I/O bursts in seconds.

iops_rd=<iops>
Maximum read I/O in operations per second.

iops_rd_max=<iops>
Maximum unthrottled read I/O pool in operations per second.

iops_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

iops_wr=<iops>
Maximum write I/O in operations per second.

iops_wr_max=<iops>
Maximum unthrottled write I/O pool in operations per second.

iops_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

mbps=<mbps>
Maximum r/w speed in megabytes per second.

mbps_max=<mbps>
Maximum unthrottled r/w pool in megabytes per second.

mbps_rd=<mbps>
Maximum read speed in megabytes per second.

mbps_rd_max=<mbps>
Maximum unthrottled read pool in megabytes per second.

mbps_wr=<mbps>
Maximum write speed in megabytes per second.

mbps_wr_max=<mbps>
Maximum unthrottled write pool in megabytes per second.


media=<cdrom | disk> (default = disk)
The drive’s media type.

model=<model>
The drive’s reported model name, url-encoded, up to 40 bytes long.

replicate=<boolean> (default = 1)
Whether the drive should considered for replication jobs.

rerror=<ignore | report | stop>
Read error action.

serial=<serial>
The drive’s reported serial number, url-encoded, up to 20 bytes long.

shared=<boolean> (default = 0)
Mark this locally-managed volume as available on all nodes.


> **Warning:**
> This option does not share the volume automatically, it assumes it is shared already!


size=<DiskSize>
Disk size. This is purely informational and has no effect.

snapshot=<boolean>
Controls qemu’s snapshot mode feature. If activated, changes made to the disk are temporary
and will be discarded when the VM is shutdown.

ssd=<boolean>
Whether to expose this drive as an SSD, rather than a rotational hard disk.

werror=<enospc | ignore | report | stop>
Write error action.

wwn=<wwn>
The drive’s worldwide name, encoded as 16 bytes hex string, prefixed by 0x.


## See also

- [VM Configuration Options: TDX, Network and IDE](configuration-options-network.md)
- [VM Configuration Options: SCSI, VirtIO and Misc](configuration-options-scsi-misc.md)
- [QEMU/KVM Overview](_index.md)
