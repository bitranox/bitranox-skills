# Hookscripts, Hibernation, and Resource Mapping

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

To handle this better, one can define cluster wide resource mappings, such that a resource has a cluster
unique, user selected identifier which can correspond to different devices on different hosts. With this, HA
won’t start a guest with a wrong device, and hardware changes can be detected.
Creating such a mapping can be done with the Proxmox VE web GUI under Datacenter in the relevant
tab in the Resource Mappings category, or on the cli with


```
# pvesh create /cluster/mapping/<type> <options>
```


Where <type> is the hardware type (currently either pci, usb or dir) and <options> are the device
mappings and other configuration parameters.
Note that the options must include a map property with all identifying properties of that hardware, so that it’s
possible to verify the hardware did not change and the correct device is passed through.
For example to add a PCI device as device1 with the path 0000:01:00.0 that has the device id 0001
and the vendor id 0002 on the node node1, and 0000:02:00.0 on node2 you can add it with:


```
# pvesh create /cluster/mapping/pci --id device1 \
--map node=node1,path=0000:01:00.0,id=0002:0001 \
--map node=node2,path=0000:02:00.0,id=0002:0001
You must repeat the map parameter for each node where that device should have a mapping (note that you
can currently only map one USB device per node per mapping).
Using the GUI makes this much easier, as the correct properties are automatically picked up and sent to the
API.
```


It’s also possible for PCI devices to provide multiple devices per node with multiple map properties for the
nodes. If such a device is assigned to a guest, the first free one will be used when the guest is started.
The order of the paths given is also the order in which they are tried, so arbitrary allocation policies can be
implemented.
This is useful for devices with SR-IOV, since some times it is not important which exact virtual function is
passed through.
You can assign such a device to a guest either with the GUI or with


```
# qm set ID -hostpci0 <name>
for PCI devices, or

# qm set <vmid> -usb0 <name>
for USB devices.
Where <vmid> is the guests id and <name> is the chosen name for the created mapping. All usual options
for passing through the devices are allowed, such as mdev.
To create mappings Mapping.Modify on /mapping/<type>/<name> is necessary (where <type>
is the device type and <name> is the name of the mapping).
To use these mappings, Mapping.Use on /mapping/<type>/<name> is necessary (in addition to
the normal guest privileges to edit the configuration).
```


Additional Options
There are additional options when defining a cluster wide resource mapping. Currently there are the following
options:

- mdev (PCI): This marks the PCI device as being capable of providing mediated devices. When this
is enabled, you can select a type when configuring it on the guest. If multiple PCI devices are selected for
the mapping, the mediated device will be created on the first one where there are any available instances
of the selected type.

- live-migration-capable (PCI): This marks the PCI device as being capable of being live migrated
between nodes. This requires driver and hardware support. Only NVIDIA GPUs with recent kernel are
known to support this. Note that live migrating passed through devices is an experimental feature and may
not work or cause issues.


## 10.13 Managing Virtual Machines with qm


```
qm is the tool to manage QEMU/KVM virtual machines on Proxmox VE. You can create and destroy virtual machines, and control execution (start/stop/suspend/resume). Besides that, you can use qm to set
```

parameters in the associated config file. It is also possible to create and delete virtual disks.


### 10.13.1 CLI Usage Examples


Using an iso file uploaded on the local storage, create a VM with a 4 GB IDE disk on the local-lvm storage


```
# qm create 300 -ide0 local-lvm:4 -net0 e1000 -cdrom local:iso/proxmox- ←mailgateway_2.1.iso
Start the new VM

# qm start 300
Send a shutdown request, then wait until the VM is stopped.

# qm shutdown 300 && qm wait 300
Same as above, but only wait for 40 seconds.

# qm shutdown 300 && qm wait 300 -timeout 40
If the VM does not shut down, force-stop it and overrule any running shutdown tasks. As stopping VMs may
incur data loss, use it with caution.

# qm stop 300 -overrule-shutdown 1
Destroying a VM always removes it from Access Control Lists and it always removes the firewall configuration
of the VM. You have to activate --purge, if you want to additionally remove the VM from replication jobs,
backup jobs and HA resource configurations.
Note
Activating purge will also remove the HA resource from any affinity rules referencing it and will remove
rules that have only this one remaining resource.

# qm destroy 300 --purge
Move a disk image to a different storage.

# qm move-disk 300 scsi0 other-storage
Reassign a disk image to a different VM. This will remove the disk scsi1 from the source VM and attaches
it as scsi3 to the target VM. In the background the disk image is being renamed so that the name matches
the new owner.

# qm move-disk 300 scsi1 --target-vmid 400 --target-disk scsi3
```


## 10.14 Configuration


VM configuration files are stored inside the Proxmox cluster file system, and can be accessed at /etc/pve/qemu
Like other files stored inside /etc/pve/, they get automatically replicated to all other cluster nodes.

> **Note:**
> VMIDs < 100 are reserved for internal purposes, and VMIDs need to be unique cluster wide.


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
