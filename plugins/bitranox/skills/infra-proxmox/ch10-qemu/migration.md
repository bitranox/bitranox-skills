# VM Migration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

How it works
Online migration first starts a new QEMU process on the target host with the incoming flag, which performs
only basic initialization with the guest vCPUs still paused and then waits for the guest memory and device
state data streams of the source Virtual Machine. All other resources, such as disks, are either shared or
got already sent before runtime state migration of the VMs begins; so only the memory content and device
state remain to be transferred.
Once this connection is established, the source begins asynchronously sending the memory content to the
target. If the guest memory on the source changes, those sections are marked dirty and another pass is
made to send the guest memory data. This loop is repeated until the data difference between running source
VM and incoming target VM is small enough to be sent in a few milliseconds, because then the source VM
can be paused completely, without a user or program noticing the pause, so that the remaining data can be
sent to the target, and then unpause the targets VM’s CPU to make it the new running VM in well under a
second.

Requirements
For Live Migration to work, there are some things required:

- The VM has no local resources that cannot be migrated. For example, PCI or USB devices that are passed
through currently block live-migration. Local Disks, on the other hand, can be migrated by sending them
to the target just fine.

- The hosts are located in the same Proxmox VE cluster.
- The hosts have a working (and reliable) network connection between them.
- The target host must have the same, or higher versions of the Proxmox VE packages. Although it can
sometimes work the other way around, this cannot be guaranteed.

- The hosts have CPUs from the same vendor with similar capabilities. Different vendor might work depending on the actual models and VMs CPU type configured, but it cannot be guaranteed - so please test
before deploying such a setup in production.

Conntrack State Migration

> **Note:**
> Conntrack state migration is considered best-effort only and might not work, as it heavily depends on the
> network setup. For example, setups using source address masquerading (SNAT) on the host will most
> likely not work.


Conntrack is a Linux kernel mechanism to enable a stateful firewall by tracking individual connection. When
live migrating running VMs, active in- and/or outbound connections might get interrupted as soon as the VM
starts running on the target host, as the new host node does not have the same conntrack entries and thus
the firewall can drop packets.
Conntrack state migration copies all conntrack entries on the host for the live-migrated VM to the target node
and afterwards flushes the migrated entries from the conntrack table on the source node.


### 10.3.2 Offline Migration


If you have local resources, you can still migrate your VMs offline as long as all disk are on storage defined
on both hosts. Migration then copies the disks to the target host over the network, as with online migration.
Note that any hardware passthrough configuration may need to be adapted to the device location on the
target host.


## 10.4 Copies and Clones


VM installation is usually done using an installation media (CD-ROM) from the operating system vendor.
Depending on the OS, this can be a time consuming task one might want to avoid.
An easy way to deploy many VMs of the same type is to copy an existing VM. We use the term clone for
such copies, and distinguish between linked and full clones.

Full Clone
The result of such copy is an independent VM. The new VM does not share any storage resources
with the original.
It is possible to select a Target Storage, so one can use this to migrate a VM to a totally different
storage. You can also change the disk image Format if the storage driver supports several formats.

> **Note:**
> A full clone needs to read and copy all VM image data. This is usually much slower than creating a
> linked clone.


Some storage types allows to copy a specific Snapshot, which defaults to the current VM data. This
also means that the final copy never includes any additional snapshots from the original VM.
Linked Clone
Modern storage drivers support a way to generate fast linked clones. Such a clone is a writable copy
whose initial contents are the same as the original data. Creating a linked clone is nearly instantaneous, and initially consumes no additional space.
They are called linked because the new image still refers to the original. Unmodified data blocks are
read from the original image, but modification are written (and afterwards read) from a new location.
This technique is called Copy-on-write.
This requires that the original volume is read-only. With Proxmox VE one can convert any VM into a
read-only Template). Such templates can later be used to create linked clones efficiently.


> **Note:**
> You cannot delete an original template while linked clones exist.


It is not possible to change the Target storage for linked clones, because this is a storage internal
feature.
The Target node option allows you to create the new VM on a different node. The only restriction is that the
VM is on shared storage, and that storage is also available on the target node.
To avoid resource conflicts, all network interface MAC addresses get randomized, and we generate a new
UUID for the VM BIOS (smbios1) setting.


## 10.5 Virtual Machine Templates


One can convert a VM into a Template. Such templates are read-only, and you can use them to create linked
clones.

> **Note:**
> It is not possible to start templates, because this would modify the disk images. If you want to change the
> template, create a linked clone and modify that.


## 10.6 VM Generation ID


Proxmox VE supports Virtual Machine Generation ID (vmgenid) 13 for virtual machines. This can be used
by the guest operating system to detect any event resulting in a time shift event, for example, restoring a
backup or a snapshot rollback.
When creating new VMs, a vmgenid will be automatically generated and saved in its configuration file.
To create and add a vmgenid to an already existing VM one can pass the special value ‘1’ to let Proxmox VE
autogenerate one or manually set the UUID 14 by using it as value, for example:


```
# qm set VMID -vmgenid 1
# qm set VMID -vmgenid 00000000-0000-0000-0000-000000000000
```


> **Note:**
> The initial addition of a vmgenid device to an existing VM, may result in the same effects as a change on
> snapshot rollback, backup restore, etc., has as the VM can interpret this as generation change.


In the rare case the vmgenid mechanism is not wanted one can pass ‘0’ for its value on VM creation, or
retroactively delete the property in the configuration with:
13 Official vmgenid Specification https://docs.microsoft.com/en-us/windows/desktop/hyperv_v2/virtual-machine-generation-

identifier
14 Online GUID generator http://guid.one/


```
# qm set VMID -delete vmgenid
The most prominent use case for vmgenid are newer Microsoft Windows operating systems, which use it
to avoid problems in time sensitive or replicate services (such as databases or domain controller 15 ) on
snapshot rollback, backup restore or a whole VM clone operation.
```


## 10.7 Importing Virtual Machines


Importing existing virtual machines from foreign hypervisors or other Proxmox VE clusters can be achieved
through various methods, the most common ones are:

- Using the native import wizard, which utilizes the import content type, such as provided by the ESXi special
storage.

- Performing a backup on the source and then restoring on the target. This method works best when
migrating from another Proxmox VE instance.

- using the OVF-specific import command of the qm command-line tool.
If you import VMs to Proxmox VE from other hypervisors, it’s recommended to familiarize yourself with the
concepts of Proxmox VE.
15 https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/virtualized-domain-controllerarchitecture
