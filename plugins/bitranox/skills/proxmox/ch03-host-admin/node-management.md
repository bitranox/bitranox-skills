# Proxmox Node Management

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Creating a snapshot of a subvolume
BTRFS does not actually distinguish between snapshots and normal subvolumes, so taking a snapshot can
also be seen as creating an arbitrary copy of a subvolume. By convention, Proxmox VE will use the read-only
flag when creating snapshots of guest disks or subvolumes, but this flag can also be changed later on.


```
# btrfs subvolume snapshot -r /some/path /a/new/path
This will create a read-only "clone" of the subvolume on /some/path at /a/new/path. Any future
modifications to /some/path cause the modified data to be copied before modification.
If the read-only (-r) option is left out, both subvolumes will be writable.
Enabling compression
By default, BTRFS does not compress data. To enable compression, the compress mount option can be
added. Note that data already written will not be compressed after the fact.
By default, the rootfs will be listed in /etc/fstab as follows:
```


UUID=<uuid of your root file system> / btrfs defaults 0 1
You can simply append compress=zstd, compress=lzo, or compress=zlib to the defaults
above like so:

UUID=<uuid of your root file system> / btrfs defaults,compress=zstd 0 1
This change will take effect after rebooting.
Checking Space Usage
The classic df tool may output confusing values for some BTRFS setups. For a better estimate use the
btrfs filesystem usage /PATH command, for example:


```
# btrfs fi usage /my-storage
```


## 3.11 Proxmox Node Management


The Proxmox VE node management tool (pvenode) allows you to control node specific settings and resources.
Currently pvenode allows you to set a node’s description, run various bulk operations on the node’s guests,
view the node’s task history, and manage the node’s SSL certificates, which are used for the API and the
web GUI through pveproxy.


### 3.11.1 Wake-on-LAN


Wake-on-LAN (WoL) allows you to switch on a sleeping computer in the network, by sending a magic packet.
At least one NIC must support this feature, and the respective option needs to be enabled in the computer’s
firmware (BIOS/UEFI) configuration. The option name can vary from Enable Wake-on-Lan to Power On By
PCIE Device; check your motherboard’s vendor manual, if you’re unsure. ethtool can be used to check
the WoL configuration of <interface> by running:


ethtool <interface> | grep Wake-on


```
pvenode allows you to wake sleeping members of a cluster via WoL, using the command:
```


```
pvenode wakeonlan <node>
```

This broadcasts the WoL magic packet on UDP port 9, containing the MAC address of <node> obtained
from the wakeonlan property. The node-specific wakeonlan property can be set using the following
command:


```
pvenode config set -wakeonlan XX:XX:XX:XX:XX:XX
```

The interface via which to send the WoL packet is determined from the default route. It can be overwritten
by setting the bind-interface via the following command:


```
pvenode config set -wakeonlan XX:XX:XX:XX:XX:XX,bind-interface=<iface-name>
```

The broadcast address (default 255.255.255.255) used when sending the WoL packet can further be
changed by setting the broadcast-address explicitly using the following command:


```
pvenode config set -wakeonlan XX:XX:XX:XX:XX:XX,broadcast-address=< ←broadcast-address>
```


### 3.11.2 Task History


When troubleshooting server issues, for example, failed backup jobs, it can often be helpful to have a log of
the previously run tasks. With Proxmox VE, you can access the nodes’s task history through the pvenode
task command.
You can get a filtered list of a node’s finished tasks with the list subcommand. For example, to get a list
of tasks related to VM 100 that ended with an error, the command would be:


```
pvenode task list --errors --vmid 100
```

The log of a task can then be printed using its UPID:


```
pvenode task log UPID:pve1:00010D94:001CA6EA:6124E1B9:vzdump:100:root@pam:
```


### 3.11.3 Bulk Guest Power Management


In case you have many VMs/containers, starting and stopping guests can be carried out in bulk operations
with the startall and stopall subcommands of pvenode. By default, pvenode startall will
only start VMs/containers which have been set to automatically start on boot (see Automatic Start and
Shutdown of Virtual Machines), however, you can override this behavior with the --force flag. Both
commands also have a --vms option, which limits the stopped/started guests to the specified VMIDs.
For example, to start VMs 100, 101, and 102, regardless of whether they have onboot set, you can use:


```
pvenode startall --vms 100,101,102 --force
```

To stop these guests (and any other guests that may be running), use the command:


```
pvenode stopall
```


> **Note:**
> The stopall command first attempts to perform a clean shutdown and then waits until either all guests have
> successfully shut down or an overridable timeout (3 minutes by default) has expired. Once that happens
> and the force-stop parameter is not explicitly set to 0 (false), all virtual guests that are still running are hard
> stopped.


### 3.11.4 First Guest Boot Delay


In case your VMs/containers rely on slow-to-start external resources, for example an NFS server, you can
also set a per-node delay between the time Proxmox VE boots and the time the first VM/container that is
configured to autostart boots (see Automatic Start and Shutdown of Virtual Machines).
You can achieve this by setting the following (where 10 represents the delay in seconds):


```
pvenode config set --startall-onboot-delay 10
```


### 3.11.5 Bulk Guest Migration


In case an upgrade situation requires you to migrate all of your guests from one node to another, pvenode
also offers the migrateall subcommand for bulk migration. By default, this command will migrate every
guest on the system to the target node. It can however be set to only migrate a set of guests.
For example, to migrate VMs 100, 101, and 102, to the node pve2, with live-migration for local disks enabled,
you can run:


```
pvenode migrateall pve2 --vms 100,101,102 --with-local-disks
```


### 3.11.6 RAM Usage Target for Ballooning


The target percentage for automatic memory allocation defaults to 80%. You can customize this target per
node by setting the ballooning-target property. For example, to target 90% host memory usage
instead:


```
pvenode config set --ballooning-target 90
```


## 3.12 Certificate Management


### 3.12.1 Certificates for Intra-Cluster Communication


Each Proxmox VE cluster creates by default its own (self-signed) Certificate Authority (CA) and generates
a certificate for each node which gets signed by the aforementioned CA. These certificates are used for
encrypted communication with the cluster’s pveproxy service and the Shell/Console feature if SPICE is
used.
The CA certificate and key are stored in the Proxmox Cluster File System (pmxcfs).

## See also

- [pvenode CLI Reference](../appendix-a-cli/pvenode.md)

