# Managing VMs with qm

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Example VM Configuration

boot: order=virtio0;net0
cores: 1
sockets: 1
memory: 512
name: webmail
ostype: l26
net0: e1000=EE:D2:28:5F:B6:3E,bridge=vmbr0
virtio0: local:vm-100-disk-1,size=32G
Those configuration files are simple text files, and you can edit them using a normal text editor (vi, nano,
. . . ). This is sometimes useful to do small corrections, but keep in mind that you need to restart the VM to
apply such changes.
For that reason, it is usually better to use the qm command to generate and modify those files, or do the
whole thing using the GUI. Our toolkit is smart enough to instantaneously apply most changes to running
VM. This feature is called "hot plug", and there is no need to restart the VM in that case.


### 10.14.1 File Format


VM configuration files use a simple colon separated key/value format. Each line has the following format:

# this is a comment
OPTION: value
Blank lines in those files are ignored, and lines starting with a # character are treated as comments and are
also ignored.


### 10.14.2 Snapshots


When you create a snapshot, qm stores the configuration at snapshot time into a separate snapshot section within the same configuration file. For example, after creating a snapshot called “testsnapshot”, your
configuration file will look like this:
VM configuration with snapshot

memory: 512
swap: 512
parent: testsnaphot
...
[testsnaphot]
memory: 512
swap: 512
snaptime: 1457170803
...
There are a few snapshot related properties like parent and snaptime. The parent property is used
to store the parent/child relationship between snapshots. snaptime is the snapshot creation time stamp
(Unix epoch).


You can optionally save the memory of a running VM with the option vmstate. For details about how the
target storage gets chosen for the VM state, see State storage selection in the chapter Hibernation.


### 10.14.3 Options


acpi: <boolean> (default = 1)
Enable/disable ACPI.

affinity: <string>
List of host cores used to execute guest processes, for example: 0,5,8-11

agent: [enabled=]<1|0> [,freeze-fs-on-backup=<1|0>]
[,fstrim_cloned_disks=<1|0>] [,type=<virtio|isa>]
Enable/disable communication with the QEMU Guest Agent and its properties.

enabled=<boolean> (default = 0)
Enable/disable communication with a QEMU Guest Agent (QGA) running in the VM.

freeze-fs-on-backup=<boolean> (default = 1)
Freeze/thaw guest filesystems on backup for consistency.

fstrim_cloned_disks=<boolean> (default = 0)
Run fstrim after moving a disk or migrating the VM.

type=<isa | virtio> (default = virtio)
Select the agent type

allow-ksm: <boolean> (default = 1)
Allow memory pages of this guest to be merged via KSM (Kernel Samepage Merging).

amd-sev: [type=]<sev-type> [,allow-smt=<1|0>] [,kernel-hashes=<1|0>]
[,no-debug=<1|0>] [,no-key-sharing=<1|0>]
Secure Encrypted Virtualization (SEV) features by AMD CPUs

allow-smt=<boolean> (default = 1)
Sets policy bit to allow Simultaneous Multi Threading (SMT) (Ignored unless for SEV-SNP)

kernel-hashes=<boolean> (default = 0)
Add kernel hashes to guest firmware for measured linux kernel launch

no-debug=<boolean> (default = 0)
Sets policy bit to disallow debugging of guest

no-key-sharing=<boolean> (default = 0)
Sets policy bit to disallow key sharing with other guests (Ignored for SEV-SNP)


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

## See also

- [qm CLI Reference](../appendix-a-cli/qm.md)

