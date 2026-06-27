# Proxmox Container Toolkit

*[Main Index](../SKILL.md)*

## Contents

| Section                                         | File                                                               |
|-------------------------------------------------|--------------------------------------------------------------------|
| 11.1-11.2 Technology Overview and Distributions | [technology-and-distributions.md](technology-and-distributions.md) |
| 11.3 Container Images                           | [container-images.md](container-images.md)                         |
| 11.4 Container Settings                         | [container-settings.md](container-settings.md)                     |
| 11.5-11.6 Security and OS Configuration         | [security-and-os-config.md](security-and-os-config.md)             |
| 11.7 Container Storage                          | [container-storage.md](container-storage.md)                       |
| 11.8-11.11 Backup, Migration, and Configuration | [backup-migration-config.md](backup-migration-config.md)           |
| 11.12 Container Locks                           | [locks.md](locks.md)                                               |


## See also

- [pct CLI Reference](../appendix-a-cli/pct.md)
- [Backup and Restore](../ch16-backup-restore/_index.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)

## Overview

Containers are a lightweight alternative to fully virtualized machines (VMs). They use the kernel of the host
system that they run on, instead of emulating a full operating system (OS). This means that containers can
access resources on the host system directly.
The runtime costs for containers is low, usually negligible. However, there are some drawbacks that need be
considered:

- Only Linux distributions can be run in Proxmox Containers. It is not possible to run other operating systems
like, for example, FreeBSD or Microsoft Windows inside a container.

- For security reasons, access to host resources needs to be restricted. Therefore, containers run in their
own separate namespaces. Additionally some syscalls (user space requests to the Linux kernel) are not
allowed within containers.
Proxmox VE uses Linux Containers (LXC) as its underlying container technology. The “Proxmox Container
Toolkit” (pct) simplifies the usage and management of LXC, by providing an interface that abstracts complex
tasks.
Containers are tightly integrated with Proxmox VE. This means that they are aware of the cluster setup, and
they can use the same network and storage resources as virtual machines. You can also use the Proxmox
VE firewall, or manage containers using the HA framework.
Our primary goal has traditionally been to offer an environment that provides the benefits of using a VM, but
without the additional overhead. This means that Proxmox Containers have been primarily categorized as
“System Containers”.
With the introduction of OCI (Open Container Initiative) image support, Proxmox VE now also integrates
“Application Containers” as a technology preview. When creating a container from an OCI image, the image
is automatically converted to the LXC stack that Proxmox VE uses.
This approach allows users to benefit from a wide ecosystem of pre-packaged applications while retaining
the robust management features of Proxmox VE.
While running lightweight “Application Containers” directly offers significant advantages over a full VM, for
use cases demanding maximum isolation and the ability to live-migrate, nesting containers inside a Proxmox
QEMU VM remains a recommended practice.
