# QEMU/KVM Virtual Machines

*[Main Index](../SKILL.md)*

## Contents

| Section                                                    | File                                                                     |
|------------------------------------------------------------|--------------------------------------------------------------------------|
| 10.1-10.2.3 VM Settings: General, OS, System               | [vm-settings-general.md](vm-settings-general.md)                         |
| 10.2.4 VM Settings: Hardware                               | [vm-settings-hardware.md](vm-settings-hardware.md)                       |
| 10.2.5-10.2.6 VM CPU and Memory                            | [vm-cpu-memory.md](vm-cpu-memory.md)                                     |
| 10.2.7-10.2.9 Memory Encryption and Display                | [vm-memory-encryption-display.md](vm-memory-encryption-display.md)       |
| 10.2.10-10.2.16 USB, Audio, PCI, Boot                      | [vm-usb-pci-boot.md](vm-usb-pci-boot.md)                                 |
| 10.2.17-10.2.20 VM Settings: Advanced                      | [vm-settings-advanced.md](vm-settings-advanced.md)                       |
| 10.3 VM Migration                                          | [migration.md](migration.md)                                             |
| 10.4-10.6 Copies, Clones and Templates                     | [copies-clones-templates.md](copies-clones-templates.md)                 |
| 10.7 Importing Virtual Machines                            | [importing-vms.md](importing-vms.md)                                     |
| 10.8 Cloud-Init Support                                    | [cloud-init.md](cloud-init.md)                                           |
| 10.9 PCI(e) Passthrough                                    | [pci-passthrough.md](pci-passthrough.md)                                 |
| 10.10-10.12 Hookscripts, Hibernation, and Resource Mapping | [hookscripts-hibernation-mapping.md](hookscripts-hibernation-mapping.md) |
| 10.13 Managing VMs with qm                                 | [managing-with-qm.md](managing-with-qm.md)                               |
| 10.14 VM Configuration Options                             | [configuration-options.md](configuration-options.md)                     |
| 10.14 Config: TDX, Network, IDE                            | [configuration-options-network.md](configuration-options-network.md)     |
| 10.14 Config: SCSI, VirtIO, Misc                           | [configuration-options-scsi-misc.md](configuration-options-scsi-misc.md) |
| 10.15 VM Locks                                             | [locks.md](locks.md)                                                     |


## See also

- [qm CLI Reference](../appendix-a-cli/qm.md)
- [Backup and Restore](../ch16-backup-restore/_index.md)
- [Containers](../ch11-containers/_index.md)

## Overview

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
