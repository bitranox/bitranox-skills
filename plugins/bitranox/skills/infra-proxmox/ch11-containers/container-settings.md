# Container Settings

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

cpulimit:

cpuunits:


### 11.4.3 You can use this option to further limit assigned CPU time. Please note that this is a

floating point number, so it is perfectly valid to assign two cores to a container, but
restrict overall CPU consumption to half a core.

cores: 2
cpulimit: 0.5
This is a relative weight passed to the kernel scheduler. The larger the number is, the
more CPU time this container gets. Number is relative to the weights of all the other
running containers. The default is 100 (or 1024 if the host uses legacy cgroup v1).
You can use this setting to prioritize some containers.

Memory

Container memory is controlled using the cgroup memory controller.

memory:
swap:

Limit overall memory usage. This corresponds to the memory.limit_in_bytes
cgroup setting.
Allows the container to use additional swap memory from the host swap space. This
corresponds to the memory.memsw.limit_in_bytes cgroup setting, which is
set to the sum of both value (memory + swap).


### 11.4.4 Mount Points


The root mount point is configured with the rootfs property. You can configure up to 256 additional mount
points. The corresponding options are called mp0 to mp255. They can contain the following settings:

rootfs: [volume=]<volume> [,acl=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container root. See below for a detailed description of all options.

mp[n]: [volume=]<volume> ,mp=<Path> [,acl=<1|0>] [,backup=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container mount point. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate
a new volume.

acl=<boolean>
Explicitly enable or disable ACL support.

backup=<boolean>
Whether to include the mount point in backups (only used for volume mount points).

mountoptions=<opt[;opt...]>
Extra mount options for rootfs/mps.

mp=<Path>
Path to the mount point as seen from inside the container.

> **Note:**
> Must not contain any symlinks for security reasons.


quota=<boolean>
Enable user quotas inside the container (not supported with zfs subvolumes)

replicate=<boolean> (default = 1)
Will include this volume to a storage replica job.

ro=<boolean>
Read-only mount point

shared=<boolean> (default = 0)
Mark this non-volume mount point as available on all nodes.

> **Warning:**
> This option does not share the mount point automatically, it assumes it is shared already!


size=<DiskSize>
Volume size (read only value).

volume=<volume>
Volume, device or directory to mount into the container.
Currently there are three types of mount points: storage backed mount points, bind mounts, and device
mounts.
Typical container rootfs configuration

rootfs: thin1:base-100-disk-1,size=8G

Storage Backed Mount Points
Storage backed mount points are managed by the Proxmox VE storage subsystem and come in three different flavors:

- Image based: these are raw images containing a single ext4 formatted file system.
- ZFS subvolumes: these are technically bind mounts, but with managed storage, and thus allow resizing
and snapshotting.

- Directories: passing size=0 triggers a special case where instead of a raw image a directory is created.

> **Note:**
> The special option syntax STORAGE_ID:SIZE_IN_GB for storage backed mount point volumes will
> automatically allocate a volume of the specified size on the specified storage. For example, calling


```
pct set 100 -mp0 thin1:10,mp=/path/in/container
```

will allocate a 10GB volume on the storage thin1 and replace the volume ID place holder 10 with the
allocated volume ID, and setup the moutpoint in the container at /path/in/container


Bind Mount Points
Bind mounts allow you to access arbitrary directories from your Proxmox VE host inside a container. Some
potential use cases are:

- Accessing your home directory in the guest
- Accessing an USB device directory in the guest
- Accessing an NFS mount from the host in the guest
Bind mounts are considered to not be managed by the storage subsystem, so you cannot make snapshots
or deal with quotas from inside the container. With unprivileged containers you might run into permission
problems caused by the user mapping and cannot use ACLs.

> **Note:**
> The contents of bind mount points are not backed up when using vzdump.


> **Warning:**
> For security reasons, bind mounts should only be established using source directories especially
> reserved for this purpose, e.g., a directory hierarchy under /mnt/bindmounts. Never bind
> mount system directories like /, /var or /etc into a container - this poses a great security risk.


> **Note:**
> The bind mount source path must not contain any symlinks.
> For example, to make the directory /mnt/bindmounts/shared accessible in the container with ID 100
> under the path /shared, add a configuration line such as:


mp0: /mnt/bindmounts/shared,mp=/shared
into /etc/pve/lxc/100.conf.
Or alternatively use the pct tool:


```
pct set 100 -mp0 /mnt/bindmounts/shared,mp=/shared
```

to achieve the same result.
Device Mount Points
Device mount points allow to mount block devices of the host directly into the container. Similar to bind
mounts, device mounts are not managed by Proxmox VE’s storage subsystem, but the quota and acl
options will be honored.

> **Note:**
> Device mount points should only be used under special circumstances. In most cases a storage backed
> mount point offers the same performance and a lot more features.
> Note
> The contents of device mount points are not backed up when using vzdump.


### 11.4.5 Network


You can configure up to 10 network interfaces for a single container. The corresponding options are called
net0 to net9, and they can contain the following setting:

net[n]: name=<string> [,bridge=<bridge>] [,firewall=<1|0>]
[,gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>] [,host-managed=<1|0>]
[,hwaddr=<XX:XX:XX:XX:XX:XX>] [,ip=<(IPv4/CIDR|dhcp|manual)>]
[,ip6=<(IPv6/CIDR|auto|dhcp|manual)>] [,link_down=<1|0>]
[,mtu=<integer>] [,rate=<mbps>] [,tag=<integer>]
[,trunks=<vlanid[;vlanid...]>] [,type=<veth>]
Specifies network interfaces for the container.

bridge=<bridge>
Bridge to attach the network device to.

firewall=<boolean>
Controls whether this interface’s firewall rules should be used.

gw=<GatewayIPv4>
Default gateway for IPv4 traffic.

gw6=<GatewayIPv6>
Default gateway for IPv6 traffic.

host-managed=<boolean>
Whether this interface’s IP configuration should be managed by the host.

hwaddr=<XX:XX:XX:XX:XX:XX>
A common MAC address with the I/G (Individual/Group) bit not set.


ip=<(IPv4/CIDR|dhcp|manual)>
IPv4 address in CIDR format.

ip6=<(IPv6/CIDR|auto|dhcp|manual)>
IPv6 address in CIDR format.

link_down=<boolean>
Whether this interface should be disconnected (like pulling the plug).

mtu=<integer> (64 - 65535)
Maximum transfer unit of the interface. (lxc.network.mtu)

name=<string>
Name of the network device as seen from inside the container. (lxc.network.name)

rate=<mbps>
Apply rate limiting to the interface

tag=<integer> (1 - 4094)
VLAN tag for this interface.

trunks=<vlanid[;vlanid...]>
VLAN ids to pass through the interface

type=<veth>
Network interface type.


### 11.4.6 Automatic Start and Shutdown of Containers


To automatically start a container when the host system boots, select the option Start at boot in the Options
panel of the container in the web interface or run the following command:


```
# pct set CTID -onboot 1
```


Start and Shutdown Order

If you want to fine tune the boot order of your containers, you can use the following parameters:

- Start/Shutdown order: Defines the start order priority. For example, set it to 1 if you want the CT to be
the first to be started. (We use the reverse startup order for shutdown, so a container with a start order of
1 would be the last to be shut down)


- Startup delay: Defines the interval between this container start and subsequent containers starts. For
example, set it to 240 if you want to wait 240 seconds before starting other containers.

- Shutdown timeout: Defines the duration in seconds Proxmox VE should wait for the container to be offline
after issuing a shutdown command. By default this value is set to 60, which means that Proxmox VE will
issue a shutdown request, wait 60s for the machine to be offline, and if after 60s the machine is still online
will notify that the shutdown action failed.
Please note that containers without a Start/Shutdown order parameter will always start after those where the
parameter is set, and this parameter only makes sense between the machines running locally on a host, and
not cluster-wide.
If you require a delay between the host boot and the booting of the first container, see the section on Proxmox
VE Node Management.


### 11.4.7 Hookscripts


You can add a hook script to CTs with the config property hookscript.


```
# pct set 100 -hookscript local:snippets/hookscript.pl
It will be called during various phases of the guests lifetime. For an example and documentation see the
example script under /usr/share/pve-docs/examples/guest-example-hookscript.pl.
```


## 11.5 Security Considerations


Containers use the kernel of the host system. This exposes an attack surface for malicious users. In general,
full virtual machines provide better isolation. This should be considered if containers are provided to unknown
or untrusted people.
To reduce the attack surface, LXC uses many security features like AppArmor, CGroups and kernel namespaces.


### 11.5.1 AppArmor


AppArmor profiles are used to restrict access to possibly dangerous actions. Some system calls, i.e. mount,
are prohibited from execution.
To trace AppArmor activity, use:

# dmesg | grep apparmor
Although it is not recommended, AppArmor can be disabled for a container. This brings security risks
with it. Some syscalls can lead to privilege escalation when executed within a container if the system is
misconfigured or if a LXC or Linux Kernel vulnerability exists.
To disable AppArmor for a container, add the following line to the container configuration file located at
/etc/pve/lxc/CTID.conf:

lxc.apparmor.profile = unconfined


> **Warning:**
> Please note that this is not recommended for production use.


### 11.5.2 Control Groups (cgroup)


cgroup is a kernel mechanism used to hierarchically organize processes and distribute system resources.
The main resources controlled via cgroups are CPU time, memory and swap limits, and access to device
nodes. cgroups are also used to "freeze" a container before taking snapshots.
The current version of cgroups is cgroupv2. The v1 version of the cgroup subsystem was deprecated with
the release of Proxmox VE 7.0 and removed entirely with Proxmox VE 9.0. Before Proxmox VE 7.0, a "hybrid"
mode was the default.

CGroup Version Compatibility
The main difference between pure cgroupv2 and the old hybrid environments regarding Proxmox VE is that
with cgroupv2 memory and swap are now controlled independently. The memory and swap settings for
containers can map directly to these values, whereas previously only the memory limit and the limit of the
sum of memory and swap could be limited.
Another important difference is that the devices controller is configured in a completely different way. Because of this, file system quotas are currently not supported in a pure cgroupv2 environment.
cgroupv2 support by the container’s OS is needed to run in a pure cgroupv2 environment. Containers
running systemd version 231 or newer support cgroupv2 1 , as do containers not using systemd as init
system 2 .

> **Note:**
> CentOS 7 and Ubuntu 16.10 are two prominent Linux distributions releases, which have a systemd version
> that is too old to run in a cgroupv2 environment, you can either


- Upgrade the whole distribution to a newer release. For the examples above, that could be Ubuntu 18.04
or 20.04, and CentOS 8 (or RHEL/CentOS derivatives like AlmaLinux or Rocky Linux). This has the
benefit to get the newest bug and security fixes, often also new features, and moving the EOL date in
the future.

- Upgrade the Containers systemd version. If the distribution provides a backports repository this can be
an easy and quick stop-gap measurement.

- Move the container, or its services, to a Virtual Machine. Virtual Machines have a much less interaction
with the host, that’s why one can install decades old OS versions just fine there.

1 this includes all newest major versions of container templates shipped by Proxmox VE
2 for example Alpine Linux


Changing CGroup Version
Before Proxmox VE 9.0, you could switch back to the previous version with the following kernel command-line
parameter:

systemd.unified_cgroup_hierarchy=0
See this section on editing the kernel boot command line on where to add the parameter.


## 11.6 Guest Operating System Configuration


Proxmox VE tries to detect the Linux distribution in the container, and modifies some files. Here is a short
list of things done at container startup:

set /etc/hostname
to set the container name
modify /etc/hosts
to allow lookup of the local hostname
network setup
pass the complete network setup to the container
configure DNS
pass information about DNS servers
adapt the init system
for example, fix the number of spawned getty processes
set the root password
when creating a new container
rewrite ssh_host_keys
so that each container has unique keys
randomize crontab
so that cron does not start at the same time on all containers
Changes made by Proxmox VE are enclosed by comment markers:

# --- BEGIN PVE --<data>
# --- END PVE --Those markers will be inserted at a reasonable location in the file. If such a section already exists, it will be
updated in place and will not be moved.
Modification of a file can be prevented by adding a .pve-ignore. file for it. For instance, if the file
/etc/.pve-ignore.hosts exists then the /etc/hosts file will not be touched. This can be a
simple empty file created via:
