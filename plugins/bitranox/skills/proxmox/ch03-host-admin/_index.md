# Host System Administration

*[Main Index](../SKILL.md)*

## Contents

| Section                                | File                                                                     |
|----------------------------------------|--------------------------------------------------------------------------|
| 3.1 Package Repositories               | [package-repositories.md](package-repositories.md)                       |
| 3.2 System Software Updates            | [software-updates.md](software-updates.md)                               |
| 3.3 Firmware Updates                   | [firmware-updates.md](firmware-updates.md)                               |
| 3.4 Network Configuration              | [network-configuration.md](network-configuration.md)                     |
| 3.4.7-3.5 Network Bonding, VLANs       | [network-bonding-vlans.md](network-bonding-vlans.md)                     |
| 3.5 Time Synchronization               | [time-synchronization.md](time-synchronization.md)                       |
| 3.6 External Metric Server             | [external-metrics.md](external-metrics.md)                               |
| 3.7 Disk Health Monitoring             | [disk-health.md](disk-health.md)                                         |
| 3.8 Logical Volume Manager (LVM)       | [lvm.md](lvm.md)                                                         |
| 3.9 ZFS on Linux                       | [zfs.md](zfs.md)                                                         |
| 3.9.6 ZFS Administration               | [zfs-administration.md](zfs-administration.md)                           |
| 3.9.10 ZFS Encryption, Compression     | [zfs-advanced.md](zfs-advanced.md)                                       |
| 3.10 BTRFS                             | [btrfs.md](btrfs.md)                                                     |
| 3.11 Proxmox Node Management           | [node-management.md](node-management.md)                                 |
| 3.12 Certificate Management            | [certificate-management.md](certificate-management.md)                   |
| 3.13 Host Bootloader                   | [host-bootloader.md](host-bootloader.md)                                 |
| 3.13.4 GRUB, Systemd-boot, Secure Boot | [host-bootloader-grub-secureboot.md](host-bootloader-grub-secureboot.md) |
| 3.14 Kernel Samepage Merging (KSM)     | [ksm.md](ksm.md)                                                         |


## See also

- [Installation](../ch02-installation.md)
- [Storage](../ch07-storage/_index.md)

## Overview

The following sections will focus on common virtualization tasks and explain the Proxmox VE specifics regarding the administration and management of the host machine.
Proxmox VE is based on Debian GNU/Linux with additional repositories to provide the Proxmox VE related
packages. This means that the full range of Debian packages is available including security updates and
bug fixes. Proxmox VE provides its own Linux kernel based on the Ubuntu kernel. It has all the necessary
virtualization and container features enabled and includes ZFS and several extra hardware drivers.
For other topics not included in the following sections, please refer to the Debian documentation. The Debian Administrator’s Handbook is available online, and provides a comprehensive introduction to the Debian
operating system (see [Hertzog13]).


## 3.1 Package Repositories


Proxmox VE uses APT as its package management tool like any other Debian-based system.
Proxmox VE automatically checks for package updates on a daily basis. The root@pam user is notified via
email about available updates. From the GUI, the Changelog button can be used to see more details about
an selected update.


### 3.1.1 Repositories in Proxmox VE


Repositories are a collection of software packages, they can be used to install new software, but are also
important to get new updates.

> **Note:**
> You need valid Debian and Proxmox repositories to get the latest security updates, bug fixes and new
> features.


APT Repositories are defined in the file /etc/apt/sources.list in the legacy single-line format and
