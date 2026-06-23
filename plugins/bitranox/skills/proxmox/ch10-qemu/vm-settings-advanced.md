# VM Settings: Advanced

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


Start and Shutdown Order

In some case you want to be able to fine tune the boot order of your VMs, for instance if one of your VM is
providing firewalling or DHCP to other guest systems. For this you can use the following parameters:

- Start/Shutdown order: Defines the start order priority. For example, set it to 1 if you want the VM to be
the first to be started. (We use the reverse startup order for shutdown, so a machine with a start order
of 1 would be the last to be shut down). If multiple VMs have the same order defined on a host, they will
additionally be ordered by VMID in ascending order.

- Startup delay: Defines the interval between this VM start and subsequent VMs starts. For example, set it
to 240 if you want to wait 240 seconds before starting other VMs.

- Shutdown timeout: Defines the duration in seconds Proxmox VE should wait for the VM to be offline after
issuing a shutdown command. By default this value is set to 180, which means that Proxmox VE will issue
a shutdown request and wait 180 seconds for the machine to be offline. If the machine is still online after
the timeout it will be stopped forcefully.

> **Note:**
> VMs managed by the HA stack do not follow the start on boot and boot order options currently. Those
> VMs will be skipped by the startup and shutdown algorithm as the HA manager itself ensures that VMs
> get started and stopped.


Please note that machines without a Start/Shutdown order parameter will always start after those where the
parameter is set. Further, this parameter can only be enforced between virtual machines running on the
same host, not cluster-wide.
If you require a delay between the host boot and the booting of the first VM, see the section on Proxmox VE
Node Management.


### 10.2.19 QEMU Guest Agent


The QEMU Guest Agent is a service which runs inside the VM, providing a communication channel between
the host and the guest. It is used to exchange information and allows the host to issue commands to the
guest.
For example, the IP addresses in the VM summary panel are fetched via the guest agent.
Or when starting a backup, the guest is told via the guest agent to sync outstanding writes via the fs-freeze
and fs-thaw commands.
For the guest agent to work properly the following steps must be taken:

- install the agent in the guest and make sure it is running
- enable the communication via the agent in Proxmox VE


Install Guest Agent
For most Linux distributions, the guest agent is available. The package is usually named qemu-guest-agent.
For Windows, it can be installed from the Fedora VirtIO driver ISO.
Enable Guest Agent Communication
Communication from Proxmox VE with the guest agent can be enabled in the VM’s Options panel. A fresh
start of the VM is necessary for the changes to take effect.
Automatic TRIM Using QGA
It is possible to enable the Run guest-trim option. With this enabled, Proxmox VE will issue a trim command
to the guest after the following operations that have the potential to write out zeros to the storage:

- moving a disk to another storage
- live migrating a VM to another node with local storage
On a thin provisioned storage, this can help to free up unused space.

> **Note:**
> There is a caveat with ext4 on Linux, because it uses an in-memory optimization to avoid issuing duplicate
> TRIM requests. Since the guest doesn’t know about the change in the underlying storage, only the first
> guest-trim will run as expected. Subsequent ones, until the next reboot, will only consider parts of the
> filesystem that changed since then.


Filesystem Freeze & Thaw
By default, if the QEMU Guest Agent is enabled in the guest’s config and if the agent is available inside of
the guest, then the virtual machine’s filesystems are synced via the fs-freeze QEMU Guest Agent command
when certain operations are performed. This is done to provide data consistency.
An fs-freeze will be issued for any of the following operations on a VM:

- Performing a backup in snapshot mode
- Creating a clone of a VM while it is running
- Replicating a VM while it is running
- Taking a snapshot without RAM of a running VM
On Windows guests, some applications might handle consistent backups themselves by hooking into the
Windows VSS (Volume Shadow Copy Service) layer, a fs-freeze then might interfere with that. For example,
it has been observed that calling fs-freeze with some SQL Servers triggers VSS to call the SQL Writer VSS
module in a mode that breaks the SQL Server backup chain for differential backups.
There are two options on how to handle such a situation.


1. Configure the QEMU Guest Agent to use a different VSS variant that does not interfere with other VSS
users. The Proxmox VE wiki has more details.
2. Alternatively, you can configure Proxmox VE to not issue a freeze-and-thaw cycle on backup by setting the freeze-fs-on-backup QGA option to 0. This can also be done via the GUI with the
Freeze/thaw guest filesystems on backup for consistency option.


> **Important:**
> Disabling this option can potentially lead to backups with inconsistent filesystems. Therefore,
> adapting the QEMU Guest Agent configuration in the guest is the preferred option.


Troubleshooting
VM does not shut down
Make sure the guest agent is installed and running.
Once the guest agent is enabled, Proxmox VE will send power commands like shutdown via the guest agent.
If the guest agent is not running, commands cannot get executed properly and the shutdown command will
run into a timeout.


### 10.2.20 SPICE Enhancements


SPICE Enhancements are optional features that can improve the remote viewer experience.
To enable them via the GUI go to the Options panel of the virtual machine. Run the following command to
enable them via the CLI:


```
qm set <vmid> -spice_enhancements foldersharing=1,videostreaming=all
```


> **Note:**
> To use these features the Display of the virtual machine must be set to SPICE (qxl).


Folder Sharing
Share a local folder with the guest. The spice-webdavd daemon needs to be installed in the guest. It
makes the shared folder available through a local WebDAV server located at http://localhost:9843.
For Windows guests the installer for the Spice WebDAV daemon can be downloaded from the official SPICE
website.
Most Linux distributions have a package called spice-webdavd that can be installed.
To share a folder in Virt-Viewer (Remote Viewer) go to File → Preferences. Select the folder to share and
then enable the checkbox.

> **Note:**
> Folder sharing currently only works in the Linux version of Virt-Viewer.


> **Caution:**
> Experimental! Currently this feature does not work reliably.


Video Streaming
Fast refreshing areas are encoded into a video stream. Two options exist:

- all: Any fast refreshing area will be encoded into a video stream.
- filter: Additional filters are used to decide if video streaming should be used (currently only small window
surfaces are skipped).
A general recommendation if video streaming should be enabled and which option to choose from cannot
be given. Your mileage may vary depending on the specific circumstances.
Troubleshooting
Shared folder does not show up
Make sure the WebDAV service is enabled and running in the guest. On Windows it is called Spice webdav
proxy. In Linux the name is spice-webdavd but can be different depending on the distribution.
If the service is running, check the WebDAV server by opening http://localhost:9843 in a browser in the guest.
It can help to restart the SPICE session.


## 10.3 Migration


If you have a cluster, you can migrate your VM to another host with


```
# qm migrate <vmid> <target>
There are generally two mechanisms for this
```


- Online Migration (aka Live Migration)
- Offline Migration


### 10.3.1 Online Migration


If your VM is running and no locally bound resources are configured (such as devices that are passed
through), you can initiate a live migration with the --online flag in the qm migration command evocation. The web interface defaults to live migration when the VM is running.


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
