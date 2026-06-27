# pct - Proxmox Container Toolkit

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

A.11


```
pct - Proxmox Container Toolkit
```


```
pct <COMMAND> [ARGS] [OPTIONS]
```


```
pct clone <vmid> <newid> [OPTIONS]
```

Create a container clone/copy

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<newid>: <integer> (100 - 999999999)
VMID for the clone.

- `--bwlimit` <number> (0 - N) (default = clone limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--description` <string>
Description for the new CT.

- `--full` <boolean>
Create a full copy of all disks. This is always done when you clone a normal CT. For CT templates, we
try to create a linked clone by default.

- `--hostname` <string>
Set a hostname for the new CT.

- `--pool` <string>
Add the new CT to the specified pool.

- `--snapname` <string>
The name of the snapshot.

- `--storage` <storage ID>
Target storage for full clone.

- `--target` <string>
Target node. Only allowed if the original VM is on shared storage.

```
pct config <vmid> [OPTIONS]
```

Get container configuration.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.


- `--current` <boolean> (default = 0)
Get current values (instead of pending values).

- `--snapshot` <string>
Fetch config values from given snapshot.

```
pct console <vmid> [OPTIONS]
```

Launch a console for the specified container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--escape` \ˆ?[a-z] (default = ˆa)
Escape sequence prefix. For example to use <Ctrl+b q> as the escape sequence pass ˆb.

```
pct cpusets
```

Print the list of assigned CPU sets.

```
pct create <vmid> <ostemplate> [OPTIONS]
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


- `--restore` <boolean>
Mark this as restore task.

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
pct delsnapshot <vmid> <snapname> [OPTIONS]
```

Delete a LXC snapshot.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<snapname>: <string>
The name of the snapshot.

- `--force` <boolean>
For removal from config file, even if removing disk snapshots fails.

```
pct destroy <vmid> [OPTIONS]
```

Destroy the container (also delete all uses files).

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--destroy-unreferenced-disks` <boolean>
If set, destroy additionally all disks with the VMID from all enabled storages which are not referenced
in the config.

- `--force` <boolean> (default = 0)
Force destroy, even if running.

- `--purge` <boolean> (default = 0)
Remove container from all related configurations. For example, backup jobs, replication jobs or HA.
Related ACLs and Firewall entries will always be removed.

```
pct df <vmid>
```

Get the container’s current disk usage.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
pct enter <vmid> [OPTIONS]
```

Launch a shell for the specified container.


<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--keep-env` <boolean> (default = 1)
Keep the current environment. This option will disabled by default with PVE 9. If you rely on a preserved environment, please use this option to be future-proof.

```
pct exec <vmid> [<extra-args>] [OPTIONS]
```

Launch a command inside the specified container.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<extra-args>: <array>
Extra arguments as array

- `--keep-env` <boolean> (default = 1)
Keep the current environment. This option will disabled by default with PVE 9. If you rely on a preserved environment, please use this option to be future-proof.

```
pct fsck <vmid> [OPTIONS]
```

Run a filesystem check (fsck) on a container volume.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.


- `--device` <mp0 | mp1 | mp10 | mp100 | mp101 | mp102 | mp103 | mp104
| mp105 | mp106 | mp107 | mp108 | mp109 | mp11 | mp110 | mp111 |
mp112 | mp113 | mp114 | mp115 | mp116 | mp117 | mp118 | mp119 |
mp12 | mp120 | mp121 | mp122 | mp123 | mp124 | mp125 | mp126 |
mp127 | mp128 | mp129 | mp13 | mp130 | mp131 | mp132 | mp133 |
mp134 | mp135 | mp136 | mp137 | mp138 | mp139 | mp14 | mp140 |
mp141 | mp142 | mp143 | mp144 | mp145 | mp146 | mp147 | mp148 |
mp149 | mp15 | mp150 | mp151 | mp152 | mp153 | mp154 | mp155 |
mp156 | mp157 | mp158 | mp159 | mp16 | mp160 | mp161 | mp162 |
mp163 | mp164 | mp165 | mp166 | mp167 | mp168 | mp169 | mp17 |
mp170 | mp171 | mp172 | mp173 | mp174 | mp175 | mp176 | mp177 |
mp178 | mp179 | mp18 | mp180 | mp181 | mp182 | mp183 | mp184 |
mp185 | mp186 | mp187 | mp188 | mp189 | mp19 | mp190 | mp191 |
mp192 | mp193 | mp194 | mp195 | mp196 | mp197 | mp198 | mp199 | mp2
| mp20 | mp200 | mp201 | mp202 | mp203 | mp204 | mp205 | mp206 |
mp207 | mp208 | mp209 | mp21 | mp210 | mp211 | mp212 | mp213 |
mp214 | mp215 | mp216 | mp217 | mp218 | mp219 | mp22 | mp220 |
mp221 | mp222 | mp223 | mp224 | mp225 | mp226 | mp227 | mp228 |
mp229 | mp23 | mp230 | mp231 | mp232 | mp233 | mp234 | mp235 |
mp236 | mp237 | mp238 | mp239 | mp24 | mp240 | mp241 | mp242 |
mp243 | mp244 | mp245 | mp246 | mp247 | mp248 | mp249 | mp25 |
mp250 | mp251 | mp252 | mp253 | mp254 | mp255 | mp26 | mp27 | mp28
| mp29 | mp3 | mp30 | mp31 | mp32 | mp33 | mp34 | mp35 | mp36 |
mp37 | mp38 | mp39 | mp4 | mp40 | mp41 | mp42 | mp43 | mp44 | mp45
| mp46 | mp47 | mp48 | mp49 | mp5 | mp50 | mp51 | mp52 | mp53 |
mp54 | mp55 | mp56 | mp57 | mp58 | mp59 | mp6 | mp60 | mp61 | mp62
| mp63 | mp64 | mp65 | mp66 | mp67 | mp68 | mp69 | mp7 | mp70 |
mp71 | mp72 | mp73 | mp74 | mp75 | mp76 | mp77 | mp78 | mp79 | mp8
| mp80 | mp81 | mp82 | mp83 | mp84 | mp85 | mp86 | mp87 | mp88 |
mp89 | mp9 | mp90 | mp91 | mp92 | mp93 | mp94 | mp95 | mp96 | mp97
| mp98 | mp99 | rootfs>
A volume on which to run the filesystem check

- `--force` <boolean> (default = 0)
Force checking, even if the filesystem seems clean

```
pct fstrim <vmid> [OPTIONS]
```

Run fstrim on a chosen CT and its mountpoints, except bind or read-only mountpoints.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--ignore-mountpoints` <boolean>
Skip all mountpoints, only do fstrim on the container root.

```
pct help [OPTIONS]
```

Get help about specified command.


- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

```

## See also

- [pct commands: list through resize](pct-list-resize.md)
- [pct commands: restore through unmount](pct-restore-unmount.md)
- [Containers](../ch11-containers/_index.md)
