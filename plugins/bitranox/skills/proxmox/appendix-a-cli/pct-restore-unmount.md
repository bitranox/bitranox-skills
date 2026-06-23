# pct commands: restore through unmount

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

pct restore <vmid> <ostemplate> [OPTIONS]
```

Create or restore a container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.


<ostemplate>: <string>
The OS template or backup file.

- `--arch` <amd64 | arm64 | armhf | i386 | riscv32 | riscv64> (default =
amd64)
OS architecture type.

- `--bwlimit` <number> (0 - N) (default = restore limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--cmode` <console | shell | tty> (default = tty)
Console mode. By default, the console command tries to open a connection to one of the available
tty devices. By setting cmode to console it tries to attach to /dev/console instead. If you set cmode to
shell, it simply invokes a shell inside the container (no login).

- `--console` <boolean> (default = 1)
Attach a console device (/dev/console) to the container.

- `--cores` <integer> (1 - 8192)
The number of cores assigned to the container. A container can use all available cores by default.

- `--cpulimit` <number> (0 - 8192) (default = 0)
Limit of CPU usage.

> **Note:**
> If the computer has 2 CPUs, it has a total of 2 CPU time. Value 0 indicates no CPU limit.


- `--cpuunits` <integer> (0 - 500000) (default = cgroup v1:
v2: 100)

1024, cgroup

CPU weight for a container, will be clamped to [1, 10000] in cgroup v2.

- `--debug` <boolean> (default = 0)
Try to be more verbose. For now this only enables debug log-level on start.

- `--description` <string>
Description for the Container. Shown in the web-interface CT’s summary. This is saved as comment
inside the configuration file.

--dev[n] [[path=]<Path>] [,deny-write=<1|0>] [,gid=<integer>]
[,mode=<Octal access mode>] [,uid=<integer>]
Device to pass through to the container

- `--entrypoint` (?ˆ:[ˆ\x00-\x08\x10-\x1F\x7F]+) (default = /sbin/init)
Command to run as init, optionally with arguments; may start with an absolute path, relative path, or a
binary in $PATH.


--env
(?ˆ:(?:\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)(?:\0\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)*
The container runtime environment as NUL-separated list. Replaces any lxc.environment.runtime
entries in the config.

- `--features` [force_rw_sys=<1|0>] [,fuse=<1|0>] [,keyctl=<1|0>]
[,mknod=<1|0>] [,mount=<fstype;fstype;...>] [,nesting=<1|0>]
Allow containers access to advanced features.

- `--force` <boolean>
Allow to overwrite existing container.

- `--ha-managed` <boolean> (default = 0)
Add the CT as a HA resource after it was created.

- `--hookscript` <string>
Script that will be executed during various steps in the containers lifetime.

- `--hostname` <string>
Set a host name for the container.

- `--ignore-unpack-errors` <boolean>
Ignore errors when extracting the template.

- `--lock` <backup | create | destroyed | disk | fstrim | migrate |
mounted | rollback | snapshot | snapshot-delete>
Lock/unlock the container.

- `--memory` <integer> (16 - N) (default = 512)
Amount of RAM for the container in MB.

--mp[n] [volume=]<volume> ,mp=<Path> [,acl=<1|0>] [,backup=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container mount point. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate
a new volume.

- `--nameserver` <string>
Sets DNS server IP address for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

--net[n] name=<string> [,bridge=<bridge>] [,firewall=<1|0>]
[,gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>] [,host-managed=<1|0>]
[,hwaddr=<XX:XX:XX:XX:XX:XX>] [,ip=<(IPv4/CIDR|dhcp|manual)>]
[,ip6=<(IPv6/CIDR|auto|dhcp|manual)>] [,link_down=<1|0>]
[,mtu=<integer>] [,rate=<mbps>] [,tag=<integer>]
[,trunks=<vlanid[;vlanid...]>] [,type=<veth>]


Specifies network interfaces for the container.

- `--onboot` <boolean> (default = 0)
Specifies whether a container will be started during system bootup.

- `--ostype` <alpine | archlinux | centos | debian | devuan | fedora |
gentoo | nixos | opensuse | ubuntu | unmanaged>
OS type. This is used to setup configuration inside the container, and corresponds to lxc setup scripts
in /usr/share/lxc/config/<ostype>.common.conf. Value unmanaged can be used to skip and OS specific setup.

- `--password` <password>
Sets root password inside container.

- `--pool` <string>
Add the VM to the specified pool.

- `--protection` <boolean> (default = 0)
Sets the protection flag of the container. This will prevent the CT or CT’s disk remove/update operation.

- `--rootfs` [volume=]<volume> [,acl=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container root.

- `--searchdomain` <string>
Sets DNS search domains for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

- `--ssh-public-keys` <filepath>
Setup public SSH keys (one key per line, OpenSSH format).

- `--start` <boolean> (default = 0)
Start the CT after its creation finished successfully.

- `--startup` `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

- `--storage` <storage ID> (default = local)
Default Storage.

- `--swap` <integer> (0 - N) (default = 512)
Amount of SWAP for the container in MB.


- `--tags` <string>
Tags of the Container. This is only meta information.

- `--template` <boolean> (default = 0)
Enable/disable Template.

- `--timezone` <string>
Time zone to use in the container. If option isn’t set, then nothing will be done. Can be set to host to
match the host time zone, or an arbitrary time zone option from /usr/share/zoneinfo/zone.tab

- `--tty` <integer> (0 - 6) (default = 2)
Specify the number of tty available to the container

- `--unique` <boolean>
Assign a unique random ethernet address.

> **Note:**
> Requires option(s): restore


- `--unprivileged` <boolean> (default = 0)
Makes the container run as unprivileged user. For creation, the default is 1. For restore, the default is
the value from the backup. (Should not be modified manually.)

--unused[n] [volume=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

```
pct resume <vmid>
```

Resume the container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
pct rollback <vmid> <snapname> [OPTIONS]
```

Rollback LXC state to specified snapshot.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<snapname>: <string>
The name of the snapshot.

- `--start` <boolean> (default = 0)
Whether the container should get started after rolling back successfully


```
pct set <vmid> [OPTIONS]
```

Set container options.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--arch` <amd64 | arm64 | armhf | i386 | riscv32 | riscv64> (default =
amd64)
OS architecture type.

- `--cmode` <console | shell | tty> (default = tty)
Console mode. By default, the console command tries to open a connection to one of the available
tty devices. By setting cmode to console it tries to attach to /dev/console instead. If you set cmode to
shell, it simply invokes a shell inside the container (no login).

- `--console` <boolean> (default = 1)
Attach a console device (/dev/console) to the container.

- `--cores` <integer> (1 - 8192)
The number of cores assigned to the container. A container can use all available cores by default.

- `--cpulimit` <number> (0 - 8192) (default = 0)
Limit of CPU usage.

> **Note:**
> If the computer has 2 CPUs, it has a total of 2 CPU time. Value 0 indicates no CPU limit.


- `--cpuunits` <integer> (0 - 500000) (default = cgroup v1:
v2: 100)

1024, cgroup

CPU weight for a container, will be clamped to [1, 10000] in cgroup v2.

- `--debug` <boolean> (default = 0)
Try to be more verbose. For now this only enables debug log-level on start.

- `--delete` <string>
A list of settings you want to delete.

- `--description` <string>
Description for the Container. Shown in the web-interface CT’s summary. This is saved as comment
inside the configuration file.

--dev[n] [[path=]<Path>] [,deny-write=<1|0>] [,gid=<integer>]
[,mode=<Octal access mode>] [,uid=<integer>]
Device to pass through to the container


- `--digest` <string>
Prevent changes if current configuration file has different SHA1 digest. This can be used to prevent
concurrent modifications.

- `--entrypoint` (?ˆ:[ˆ\x00-\x08\x10-\x1F\x7F]+) (default = /sbin/init)
Command to run as init, optionally with arguments; may start with an absolute path, relative path, or a
binary in $PATH.

--env
(?ˆ:(?:\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)(?:\0\w+=[ˆ\x00-\x08\x10-\x1F\x7F]*)*
The container runtime environment as NUL-separated list. Replaces any lxc.environment.runtime
entries in the config.

- `--features` [force_rw_sys=<1|0>] [,fuse=<1|0>] [,keyctl=<1|0>]
[,mknod=<1|0>] [,mount=<fstype;fstype;...>] [,nesting=<1|0>]
Allow containers access to advanced features.

- `--hookscript` <string>
Script that will be executed during various steps in the containers lifetime.

- `--hostname` <string>
Set a host name for the container.

- `--lock` <backup | create | destroyed | disk | fstrim | migrate |
mounted | rollback | snapshot | snapshot-delete>
Lock/unlock the container.

- `--memory` <integer> (16 - N) (default = 512)
Amount of RAM for the container in MB.

--mp[n] [volume=]<volume> ,mp=<Path> [,acl=<1|0>] [,backup=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container mount point. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate
a new volume.

- `--nameserver` <string>
Sets DNS server IP address for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

--net[n] name=<string> [,bridge=<bridge>] [,firewall=<1|0>]
[,gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>] [,host-managed=<1|0>]
[,hwaddr=<XX:XX:XX:XX:XX:XX>] [,ip=<(IPv4/CIDR|dhcp|manual)>]
[,ip6=<(IPv6/CIDR|auto|dhcp|manual)>] [,link_down=<1|0>]
[,mtu=<integer>] [,rate=<mbps>] [,tag=<integer>]
[,trunks=<vlanid[;vlanid...]>] [,type=<veth>]
Specifies network interfaces for the container.


- `--onboot` <boolean> (default = 0)
Specifies whether a container will be started during system bootup.

- `--ostype` <alpine | archlinux | centos | debian | devuan | fedora |
gentoo | nixos | opensuse | ubuntu | unmanaged>
OS type. This is used to setup configuration inside the container, and corresponds to lxc setup scripts
in /usr/share/lxc/config/<ostype>.common.conf. Value unmanaged can be used to skip and OS specific setup.

- `--protection` <boolean> (default = 0)
Sets the protection flag of the container. This will prevent the CT or CT’s disk remove/update operation.

- `--revert` <string>
Revert a pending change.

- `--rootfs` [volume=]<volume> [,acl=<1|0>]
[,mountoptions=<opt[;opt...]>] [,quota=<1|0>] [,replicate=<1|0>]
[,ro=<1|0>] [,shared=<1|0>] [,size=<DiskSize>]
Use volume as container root.

- `--searchdomain` <string>
Sets DNS search domains for a container. Create will automatically use the setting from the host if
you neither set searchdomain nor nameserver.

- `--startup` `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

- `--swap` <integer> (0 - N) (default = 512)
Amount of SWAP for the container in MB.

- `--tags` <string>
Tags of the Container. This is only meta information.

- `--template` <boolean> (default = 0)
Enable/disable Template.

- `--timezone` <string>
Time zone to use in the container. If option isn’t set, then nothing will be done. Can be set to host to
match the host time zone, or an arbitrary time zone option from /usr/share/zoneinfo/zone.tab

- `--tty` <integer> (0 - 6) (default = 2)
Specify the number of tty available to the container


- `--unprivileged` <boolean> (default = 0)
Makes the container run as unprivileged user. For creation, the default is 1. For restore, the default is
the value from the backup. (Should not be modified manually.)

--unused[n] [volume=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

```
pct shutdown <vmid> [OPTIONS]
```

Shutdown the container. This will trigger a clean shutdown of the container, see lxc-stop(1) for details.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--forceStop` <boolean> (default = 0)
Make sure the Container stops.

- `--timeout` <integer> (0 - N) (default = 60)
Wait maximal timeout seconds.

```
pct snapshot <vmid> <snapname> [OPTIONS]
```

Snapshot a container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<snapname>: <string>
The name of the snapshot.

- `--description` <string>
A textual description or comment.

```
pct start <vmid> [OPTIONS]
```

Start the container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--debug` <boolean> (default = 0)
If set, enables very verbose debug log-level on start.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.


```
pct status <vmid> [OPTIONS]
```

Show CT status.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--verbose` <boolean>
Verbose output format

```
pct stop <vmid> [OPTIONS]
```

Stop the container. This will abruptly stop all processes running in the container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--overrule-shutdown` <boolean> (default = 0)
Try to abort active vzshutdown tasks before stopping.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

```
pct suspend <vmid>
```

Suspend the container. This is experimental.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
pct template <vmid>
```

Create a Template.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
pct unlock <vmid>
```

Unlock the VM.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
pct unmount <vmid>
```

Unmount the container’s filesystem.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

## See also


## See also

- [pct - Proxmox Container Toolkit](pct.md)
- [pct commands: list through resize](pct-list-resize.md)
- [Containers](../ch11-containers/_index.md)
