# VM Settings: General, OS, System

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

QEMU (short form for Quick Emulator) is an open source hypervisor that emulates a physical computer. From
the perspective of the host system where QEMU is running, QEMU is a user program which has access to a
number of local resources like partitions, files, network cards which are then passed to an emulated computer
which sees them as if they were real devices.
A guest operating system running in the emulated computer accesses these devices, and runs as if it were
running on real hardware. For instance, you can pass an ISO image as a parameter to QEMU, and the OS
running in the emulated computer will see a real CD-ROM inserted into a CD drive.
QEMU can emulate a great variety of hardware from ARM to Sparc, but Proxmox VE is only concerned with
32 and 64 bits PC clone emulation, since it represents the overwhelming majority of server hardware. The
emulation of PC clones is also one of the fastest due to the availability of processor extensions which greatly
speed up QEMU when the emulated architecture is the same as the host architecture.

> **Note:**
> You may sometimes encounter the term KVM (Kernel-based Virtual Machine). It means that QEMU is
> running with the support of the virtualization processor extensions, via the Linux KVM module. In the
> context of Proxmox VE QEMU and KVM can be used interchangeably, as QEMU in Proxmox VE will
> always try to load the KVM module.


QEMU inside Proxmox VE runs as a root process, since this is required to access block and PCI devices.


## 10.1 Emulated devices and paravirtualized devices


The PC hardware emulated by QEMU includes a motherboard, network controllers, SCSI, IDE and SATA
controllers, serial ports (the complete list can be seen in the kvm(1) man page) all of them emulated in
software. All these devices are the exact software equivalent of existing hardware devices, and if the OS
running in the guest has the proper drivers it will use the devices as if it were running on real hardware. This
allows QEMU to run unmodified operating systems.
This however has a performance cost, as running in software what was meant to run in hardware involves
a lot of extra work for the host CPU. To mitigate this, QEMU can present to the guest operating system
paravirtualized devices, where the guest OS recognizes it is running inside QEMU and cooperates with the
hypervisor.


QEMU relies on the virtio virtualization standard, and is thus able to present paravirtualized virtio devices,
which includes a paravirtualized generic disk controller, a paravirtualized network card, a paravirtualized
serial port, a paravirtualized SCSI controller, etc . . .

> **Tip:**
> It is highly recommended to use the virtio devices whenever you can, as they provide a big performance
> improvement and are generally better maintained. Using the virtio generic disk controller versus an emulated IDE controller will double the sequential write throughput, as measured with bonnie++(8). Using
> the virtio network interface can deliver up to three times the throughput of an emulated Intel E1000 network card, as measured with iperf(1). a
> a See this benchmark on the KVM wiki https://www.linux-kvm.org/page/Using_VirtIO_NIC


## 10.2 Virtual Machines Settings


Generally speaking Proxmox VE tries to choose sane defaults for virtual machines (VM). Make sure you
understand the meaning of the settings you change, as it could incur a performance slowdown, or putting
your data at risk.


### 10.2.1 General Settings


General settings of a VM include

- the Node : the physical server on which the VM will run
- the VM ID: a unique number in this Proxmox VE installation used to identify your VM
- Name: a free form text string you can use to describe the VM
- Resource Pool: a logical group of VMs


### 10.2.2 OS Settings


When creating a virtual machine (VM), setting the proper Operating System(OS) allows Proxmox VE to
optimize some low level parameters. For instance Windows OS expect the BIOS clock to use the local time,
while Unix based OS expect the BIOS clock to have the UTC time.


### 10.2.3 System Settings


On VM creation you can change some basic system components of the new VM. You can specify which
display type you want to use.

Additionally, the SCSI controller can be changed. If you plan to install the QEMU Guest Agent, or if your
selected ISO image already ships and installs it automatically, you may want to tick the QEMU Agent box,


which lets Proxmox VE know that it can use its features to show some more information, and complete some
actions (for example, shutdown or snapshots) more intelligently.
Proxmox VE allows to boot VMs with different firmware and machine types, namely SeaBIOS and OVMF. In
most cases you want to switch from the default SeaBIOS to OVMF only if you plan to use PCIe passthrough.
Machine Type
A VM’s Machine Type defines the hardware layout of the VM’s virtual motherboard. You can choose between
the default Intel 440FX or the Q35 chipset, which also provides a virtual PCIe bus, and thus may be desired
if you want to pass through PCIe hardware. Additionally, you can select a vIOMMU implementation.
Machine Version
Each machine type is versioned in QEMU and a given QEMU binary supports many machine versions.
New versions might bring support for new features, fixes or general improvements. However, they also
change properties of the virtual hardware. To avoid sudden changes from the guest’s perspective and ensure
compatibility of the VM state, live-migration and snapshots with RAM will keep using the same machine
version in the new QEMU instance.
For Windows guests, the machine version is pinned during creation, because Windows is sensitive to
changes in the virtual hardware - even between cold boots. For example, the enumeration of network devices might be different with different machine versions. Other OSes like Linux can usually deal with such
changes just fine. For those, the Latest machine version is used by default. This means that after a fresh
start, the newest machine version supported by the QEMU binary is used (e.g. the newest machine version
QEMU 8.1 supports is version 8.1 for each machine type).
The machine version is also used as a safeguard when implementing new features or fixes that would
change the hardware layout to ensure backward compatibility. For operations on a running VM, such as live
migrations, the running machine version is saved to ensure that the VM can be recovered exactly as it was,
not only from a QEMU virtualization perspective, but also in terms of how Proxmox VE will create the QEMU
virtual machine instance.
PVE Machine Revision
Sometimes Proxmox VE needs to make changes to the hardware layout or modify options without waiting for
a new QEMU release. For this, Proxmox VE has added an extra downstream revision in the form of +pveX.
In these revisions, X is 0 for each new QEMU machine version and is omitted in this case, e.g. machine
version pc-q35-9.2 would be the same as machine version pc-q35-9.2+pve0.
If Proxmox VE wants to change the hardware layout or a default option, the revision is incremented and used
for newly created guests or on reboot for VMs that always use the latest machine version.
QEMU Machine Version Deprecation
Starting with QEMU 10.1, machine versions are removed from upstream QEMU after 6 years. In Proxmox VE, major releases happen approximately every 2 years, so a major Proxmox VE release will support
machine versions from approximately two previous major Proxmox VE releases.
Before upgrading to a new major Proxmox VE release, you should update VM configurations to avoid all
machine versions that will be dropped during the next major Proxmox VE release. This ensures that the
guests can still be used throughout that release. See the section Update to a Newer Machine Version.


The removal policy is not yet in effect for Proxmox VE 8, so the baseline for supported machine versions is
2.4. The last QEMU binary version released for Proxmox VE 9 is expected to be QEMU 11.2. This QEMU
binary will remove support for machine versions older than 6.0, so 6.0 is the baseline for the Proxmox VE
9 release life cycle. The baseline is expected to increase by 2 major versions for each major Proxmox VE
release, for example 8.0 for Proxmox VE 10.

Update to a Newer Machine Version
If you see a deprecation warning, you should change the machine version to a newer one. Be sure to have
a working backup first and be prepared for changes to how the guest sees hardware. In some scenarios,
re-installing certain drivers might be required. You should also check for snapshots with RAM that were taken
with these machine versions (i.e. the runningmachine configuration entry). Unfortunately, there is no
way to change the machine version of a snapshot, so you’d need to load the snapshot to salvage any data
from it.


### 10.2.4 Hard Disk


Bus/Controller
QEMU can emulate a number of storage controllers:

> **Tip:**
> It is highly recommended to use the VirtIO SCSI or VirtIO Block controller for performance reasons and
> because they are better maintained.


- the IDE controller, has a design which goes back to the 1984 PC/AT disk controller. Even if this controller
has been superseded by recent designs, each and every OS you can think of has support for it, making
it a great choice if you want to run an OS released before 2003. You can connect up to 4 devices on this
controller.

- the SATA (Serial ATA) controller, dating from 2003, has a more modern design, allowing higher throughput
and a greater number of devices to be connected. You can connect up to 6 devices on this controller.

- the SCSI controller, designed in 1985, is commonly found on server grade hardware, and can connect up
to 14 storage devices. Proxmox VE emulates by default a LSI 53C895A controller.
A SCSI controller of type VirtIO SCSI single and enabling the IO Thread setting for the attached disks is
recommended if you aim for performance. This is the default for newly created Linux VMs since Proxmox
VE 7.3. Each disk will have its own VirtIO SCSI controller, and QEMU will handle the disks IO in a
dedicated thread. Linux distributions have support for this controller since 2012, and FreeBSD since 2014.
For Windows OSes, you need to provide an extra ISO containing the drivers during the installation.

- The VirtIO Block controller, often just called VirtIO or virtio-blk, is an older type of paravirtualized controller.
It has been superseded by the VirtIO SCSI Controller, in terms of features.
