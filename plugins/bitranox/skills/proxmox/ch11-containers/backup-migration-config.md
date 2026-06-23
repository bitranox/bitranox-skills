# Backup, Migration, and Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 11.9.1 CLI Usage Examples


Create a container based on a Debian template (provided you have already downloaded the template via
the web interface)


```
# pct create 100 /var/lib/vz/template/cache/debian-10.0-standard_10.0-1 ←_amd64.tar.gz
Start container 100

# pct start 100
Start a login session via getty

# pct console 100
Enter the LXC namespace and run a shell as root user

# pct enter 100
Display the configuration

# pct config 100
Add a network interface called eth0, bridged to the host bridge vmbr0, set the address and gateway, while
it’s running

# pct set 100 -net0 name=eth0,bridge=vmbr0,ip=192.168.15.147/24,gw ←=192.168.15.1
Reduce the memory of the container to 512MB

# pct set 100 -memory 512
Destroying a container always removes it from Access Control Lists and it always removes the firewall configuration of the container. You have to activate --purge, if you want to additionally remove the container from
replication jobs, backup jobs and HA resource configurations.
Note
Activating purge will also remove the HA resource from any affinity rules referencing it and will remove
rules that have only this one remaining resource.

# pct destroy 100 --purge
Move a mount point volume to a different storage.

# pct move-volume 100 mp0 other-storage
Reassign a volume to a different CT. This will remove the volume mp0 from the source CT and attaches it
as mp1 to the target CT. In the background the volume is being renamed so that the name matches the new
owner.
```


#


```
pct move-volume 100 mp0 --target-vmid 200 --target-volume mp1
```


### 11.9.2 Obtaining Debugging Logs


In case pct start is unable to start a specific container, it might be helpful to collect debugging output
by passing the --debug flag (replace CTID with the container’s CTID):


```
# pct start CTID --debug
Alternatively, you can use the following lxc-start command, which will save the debug log to the file
specified by the -o output option:

# lxc-start -n CTID -F -l DEBUG -o /tmp/lxc-CTID.log
This command will attempt to start the container in foreground mode, to stop the container run pct shutdown
CTID or pct stop CTID in a second terminal.
The collected debug log is written to /tmp/lxc-CTID.log.
Note
If you have changed the container’s configuration since the last start attempt with pct start, you need
to run pct start at least once to also update the configuration used by lxc-start.
```


## 11.10 Migration


If you have a cluster, you can migrate your Containers with


```
# pct migrate <ctid> <target>
This works as long as your Container is offline. If it has local volumes or mount points defined, the migration
will copy the content over the network to the target host if the same storage is defined there.
Running containers cannot live-migrated due to technical limitations. You can do a restart migration, which
shuts down, moves and then starts a container again on the target node. As containers are very lightweight,
this results normally only in a downtime of some hundreds of milliseconds.
A restart migration can be done through the web interface or by using the --restart flag with the pct
migrate command.
A restart migration will shut down the Container and kill it after the specified timeout (the default is 180
seconds). Then it will migrate the Container like an offline migration and when finished, it starts the Container
on the target node.
```


## 11.11 Configuration


The /etc/pve/lxc/<CTID>.conf file stores container configuration, where <CTID> is the numeric
ID of the given container. Like all other files stored inside /etc/pve/, they get automatically replicated to
all other cluster nodes.

> **Note:**
> CTIDs < 100 are reserved for internal purposes, and CTIDs need to be unique cluster wide.


Example Container Configuration

ostype: debian
arch: amd64
hostname: www
memory: 512
swap: 512
net0: bridge=vmbr0,hwaddr=66:64:66:64:64:36,ip=dhcp,name=eth0,type=veth
rootfs: local:107/vm-107-disk-1.raw,size=7G
The configuration files are simple text files. You can edit them using a normal text editor, for example, vi
or nano. This is sometimes useful to do small corrections, but keep in mind that you need to restart the
container to apply such changes.
For that reason, it is usually better to use the pct command to generate and modify those files, or do the
whole thing using the GUI. Our toolkit is smart enough to instantaneously apply most changes to running
containers. This feature is called “hot plug”, and there is no need to restart the container in that case.
In cases where a change cannot be hot-plugged, it will be registered as a pending change (shown in red
color in the GUI). They will only be applied after rebooting the container.


### 11.11.1 File Format


The container configuration file uses a simple colon separated key/value format. Each line has the following
format:

# this is a comment
OPTION: value
Blank lines in those files are ignored, and lines starting with a # character are treated as comments and are
also ignored.
It is possible to add low-level, LXC style configuration directly, for example:

lxc.init_cmd: /sbin/my_own_init
or

lxc.init_cmd = /sbin/my_own_init
The settings are passed directly to the LXC low-level tools.


### 11.11.2 Snapshots


When you create a snapshot, pct stores the configuration at snapshot time into a separate snapshot section within the same configuration file. For example, after creating a snapshot called “testsnapshot”, your
configuration file will look like this:

Container configuration with snapshot


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


### 11.11.3 Options


arch: <amd64 | arm64 | armhf | i386 | riscv32 | riscv64> (default =
amd64)
OS architecture type.

cmode: <console | shell | tty> (default = tty)
Console mode. By default, the console command tries to open a connection to one of the available
tty devices. By setting cmode to console it tries to attach to /dev/console instead. If you set cmode to
shell, it simply invokes a shell inside the container (no login).

console: <boolean> (default = 1)
Attach a console device (/dev/console) to the container.

cores: <integer> (1 - 8192)
The number of cores assigned to the container. A container can use all available cores by default.

cpulimit: <number> (0 - 8192) (default = 0)
Limit of CPU usage.

> **Note:**
> If the computer has 2 CPUs, it has a total of 2 CPU time. Value 0 indicates no CPU limit.


cpuunits: <integer> (0 - 500000) (default = cgroup v1:
100)

1024, cgroup v2:

CPU weight for a container. Argument is used in the kernel fair scheduler. The larger the number
is, the more CPU time this container gets. Number is relative to the weights of all the other running
guests.


debug: <boolean> (default = 0)
Try to be more verbose. For now this only enables debug log-level on start.

description: <string>
Description for the Container. Shown in the web-interface CT’s summary. This is saved as comment
inside the configuration file.

dev[n]: [[path=]<Path>] [,deny-write=<1|0>] [,gid=<integer>]
[,mode=<Octal access mode>] [,uid=<integer>]
Device to pass through to the container

deny-write=<boolean> (default = 0)
Deny the container to write to the device

gid=<integer> (0 - N)
Group ID to be assigned to the device node

mode=<Octal access mode>
Access mode to be set on the device node

path=<Path>
Path to the device to pass through to the container

uid=<integer> (0 - N)
User ID to be assigned to the device node

entrypoint: (?ˆ:[ˆ\x00-\x08\x10-\x1F\x7F]+) (default = /sbin/init)
Command to run as init, optionally with arguments; may start with an absolute path, relative path, or a
binary in $PATH.

env:
(?ˆ:(?:\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)(?:\0\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)*
The container runtime environment as NUL-separated list. Replaces any lxc.environment.runtime
entries in the config.

features: [force_rw_sys=<1|0>] [,fuse=<1|0>] [,keyctl=<1|0>]
[,mknod=<1|0>] [,mount=<fstype;fstype;...>] [,nesting=<1|0>]
Allow containers access to advanced features.

force_rw_sys=<boolean> (default = 0)
Mount /sys in unprivileged containers as rw instead of mixed. This can break networking under
newer (>= v245) systemd-network use.

fuse=<boolean> (default = 0)
Allow using fuse file systems in a container. Note that interactions between fuse and the freezer
cgroup can potentially cause I/O deadlocks.


keyctl=<boolean> (default = 0)
For unprivileged containers only: Allow the use of the keyctl() system call. This is required to
use docker inside a container. By default unprivileged containers will see this system call as
non-existent. This is mostly a workaround for systemd-networkd, as it will treat it as a fatal error
when some keyctl() operations are denied by the kernel due to lacking permissions. Essentially,
you can choose between running systemd-networkd or docker.

mknod=<boolean> (default = 0)
Allow unprivileged containers to use mknod() to add certain device nodes. This requires a kernel
with seccomp trap to user space support (5.3 or newer). This is experimental.

mount=<fstype;fstype;...>
Allow mounting file systems of specific types. This should be a list of file system types as used
with the mount command. Note that this can have negative effects on the container’s security.
With access to a loop device, mounting a file can circumvent the mknod permission of the devices
cgroup, mounting an NFS file system can block the host’s I/O completely and prevent it from
rebooting, etc.

nesting=<boolean> (default = 0)
Allow nesting. Best used with unprivileged containers with additional id mapping. Note that this
will expose procfs and sysfs contents of the host to the guest. This is also required by systemd
to isolate services.

hookscript: <string>
Script that will be executed during various steps in the containers lifetime.

hostname: <string>
Set a host name for the container.

lock: <backup | create | destroyed | disk | fstrim | migrate |
mounted | rollback | snapshot | snapshot-delete>
Lock/unlock the container.

memory: <integer> (16 - N) (default = 512)
Amount of RAM for the container in MB.

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

nameserver: <string>
Sets DNS server IP address for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

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

onboot: <boolean> (default = 0)
Specifies whether a container will be started during system bootup.

ostype: <alpine | archlinux | centos | debian | devuan | fedora |
gentoo | nixos | opensuse | ubuntu | unmanaged>
OS type. This is used to setup configuration inside the container, and corresponds to lxc setup scripts
in /usr/share/lxc/config/<ostype>.common.conf. Value unmanaged can be used to skip and OS specific setup.

protection: <boolean> (default = 0)
Sets the protection flag of the container. This will prevent the CT or CT’s disk remove/update operation.


rootfs: [volume=]<volume> [,acl=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container root.

acl=<boolean>
Explicitly enable or disable ACL support.

mountoptions=<opt[;opt...]>
Extra mount options for rootfs/mps.

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

searchdomain: <string>
Sets DNS search domains for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

startup: `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

swap: <integer> (0 - N) (default = 512)
Amount of SWAP for the container in MB.

tags: <string>
Tags of the Container. This is only meta information.


template: <boolean> (default = 0)
Enable/disable Template.

timezone: <string>
Time zone to use in the container. If option isn’t set, then nothing will be done. Can be set to host to
match the host time zone, or an arbitrary time zone option from /usr/share/zoneinfo/zone.tab

tty: <integer> (0 - 6) (default = 2)
Specify the number of tty available to the container

unprivileged: <boolean> (default = 0)
Makes the container run as unprivileged user. For creation, the default is 1. For restore, the default is
the value from the backup. (Should not be modified manually.)

unused[n]: [volume=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

volume=<volume>
The volume that is not used currently.


## 11.12 Locks


Container migrations, snapshots and backups (vzdump) set a lock to prevent incompatible concurrent actions on the affected container. Sometimes you need to remove such a lock manually (e.g., after a power
failure).


```
# pct unlock <CTID>
```


> **Caution:**
> Only do this if you are sure the action which set the lock is no longer running.


## See also

- [Backup and Restore](../ch16-backup-restore/_index.md)

