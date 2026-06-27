# qm commands: set (cont.) through wait

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

If cloud-init is enabled and neither an IPv4 nor an IPv6 address is specified, it defaults to using dhcp
on IPv4.

- `--ivshmem` size=<integer> [,name=<string>]
Inter-VM shared memory. Useful for direct communication between VMs, or to the host.

- `--keephugepages` <boolean> (default = 0)
Use together with hugepages. If enabled, hugepages will not not be deleted after VM shutdown and
can be used for subsequent starts.

- `--keyboard` <da | de | de-ch | en-gb | en-us | es | fi | fr | fr-be
| fr-ca | fr-ch | hu | is | it | ja | lt | mk | nl | no | pl | pt |
pt-br | sl | sv | tr>
Keyboard layout for VNC server. This option is generally not required and is often better handled from
within the guest OS.


- `--kvm` <boolean> (default = 1)
Enable/disable KVM hardware virtualization.

- `--localtime` <boolean>
Set the real time clock (RTC) to local time. This is enabled by default if the ostype indicates a
Microsoft Windows OS.

- `--lock` <backup | clone | create | migrate | rollback | snapshot |
snapshot-delete | suspended | suspending>
Lock/unlock the VM.

- `--machine` [[type=]<machine type>] [,aw-bits=<number>]
[,enable-s3=<1|0>] [,enable-s4=<1|0>] [,viommu=<intel|virtio>]
Specify the QEMU machine.

- `--memory` [current=]<integer>
Memory properties.

- `--migrate_downtime` <number> (0 - N) (default = 0.1)
Set maximum tolerated downtime (in seconds) for migrations. Should the migration not be able to
converge in the very end, because too much newly dirtied RAM needs to be transferred, the limit will
be increased automatically step-by-step until migration can converge.

- `--migrate_speed` <integer> (0 - N) (default = 0)
Set maximum speed (in MB/s) for migrations. Value 0 is no limit.

- `--name` <string>
Set a name for the VM. Only used on the configuration web interface.

- `--nameserver` <string>
cloud-init: Sets DNS server IP address for a container. Create will automatically use the setting from
the host if neither searchdomain nor nameserver are set.

--net[n] [model=]<enum> [,bridge=<bridge>] [,firewall=<1|0>]
[,link_down=<1|0>] [,macaddr=<XX:XX:XX:XX:XX:XX>] [,mtu=<integer>]
[,queues=<integer>] [,rate=<number>] [,tag=<integer>]
[,trunks=<vlanid[;vlanid...]>] [,<model>=<macaddr>]
Specify network devices.

- `--numa` <boolean> (default = 0)
Enable/disable NUMA.

--numa[n] cpus=<id[-id];...> [,hostnodes=<id[-id];...>]
[,memory=<number>] [,policy=<preferred|bind|interleave>]
NUMA topology.


- `--onboot` <boolean> (default = 0)
Specifies whether a VM will be started during system bootup.

- `--ostype` <l24 | l26 | other | solaris | w2k | w2k3 | w2k8 | win10 |
win11 | win7 | win8 | wvista | wxp> (default = other)
Specify guest operating system.

--parallel[n] /dev/parport\d+|/dev/usb/lp\d+
Map host parallel devices (n is 0 to 2).

- `--protection` <boolean> (default = 0)
Sets the protection flag of the VM. This will disable the remove VM and remove disk operations.

- `--reboot` <boolean> (default = 1)
Allow reboot. If set to 0 the VM exit on reboot.

- `--revert` <string>
Revert a pending change.

- `--rng0` [source=]</dev/urandom|/dev/random|/dev/hwrng>
[,max_bytes=<integer>] [,period=<integer>]
Configure a VirtIO-based Random Number Generator.

--sata[n] [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,import-from=<source volume>] [,iops=<iops>] [,iops_max=<iops>]
[,iops_max_length=<seconds>] [,iops_rd=<iops>]
[,iops_rd_max=<iops>] [,iops_rd_max_length=<seconds>]
[,iops_wr=<iops>] [,iops_wr_max=<iops>]
[,iops_wr_max_length=<seconds>] [,mbps=<mbps>] [,mbps_max=<mbps>]
[,mbps_rd=<mbps>] [,mbps_rd_max=<mbps>] [,mbps_wr=<mbps>]
[,mbps_wr_max=<mbps>] [,media=<cdrom|disk>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,serial=<serial>] [,shared=<1|0>]
[,size=<DiskSize>] [,snapshot=<1|0>] [,ssd=<1|0>] [,werror=<enum>]
[,wwn=<wwn>]
Use volume as SATA hard disk or CD-ROM (n is 0 to 5). Use the special syntax STORAGE_ID:SIZE_IN_GiB
to allocate a new volume. Use STORAGE_ID:0 and the import-from parameter to import from an existing volume.


--scsi[n] [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,import-from=<source volume>] [,iops=<iops>] [,iops_max=<iops>]
[,iops_max_length=<seconds>] [,iops_rd=<iops>]
[,iops_rd_max=<iops>] [,iops_rd_max_length=<seconds>]
[,iops_wr=<iops>] [,iops_wr_max=<iops>]
[,iops_wr_max_length=<seconds>] [,iothread=<1|0>] [,mbps=<mbps>]
[,mbps_max=<mbps>] [,mbps_rd=<mbps>] [,mbps_rd_max=<mbps>]
[,mbps_wr=<mbps>] [,mbps_wr_max=<mbps>] [,media=<cdrom|disk>]
[,product=<product>] [,queues=<integer>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,ro=<1|0>] [,scsiblock=<1|0>]
[,serial=<serial>] [,shared=<1|0>] [,size=<DiskSize>]
[,snapshot=<1|0>] [,ssd=<1|0>] [,vendor=<vendor>] [,werror=<enum>]
[,wwn=<wwn>]

Use volume as SCSI hard disk or CD-ROM (n is 0 to 30). Use the special syntax STORAGE_ID:SIZE_IN_GiB
to allocate a new volume. Use STORAGE_ID:0 and the import-from parameter to import from an existing volume.

- `--scsihw` <lsi | lsi53c810 | megasas | pvscsi | virtio-scsi-pci |
virtio-scsi-single> (default = lsi)
SCSI controller model

- `--searchdomain` <string>
cloud-init: Sets DNS search domains for a container. Create will automatically use the setting from the
host if neither searchdomain nor nameserver are set.

--serial[n] (/dev/.+|socket)
Create a serial device inside the VM (n is 0 to 3)

- `--shares` <integer> (0 - 50000) (default = 1000)
Amount of memory shares for auto-ballooning. The larger the number is, the more memory this VM
gets. Number is relative to weights of all other running VMs. Using zero disables auto-ballooning.
Auto-ballooning is done by pvestatd.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

- `--smbios1` [base64=<1|0>] [,family=<Base64 encoded string>]
[,manufacturer=<Base64 encoded string>] [,product=<Base64 encoded
string>] [,serial=<Base64 encoded string>] [,sku=<Base64 encoded
string>] [,uuid=<UUID>] [,version=<Base64 encoded string>]
Specify SMBIOS type 1 fields.

- `--smp` <integer> (1 - N) (default = 1)
The number of CPUs. Please use option -sockets instead.


- `--sockets` <integer> (1 - N) (default = 1)
The number of CPU sockets.

- `--spice_enhancements` [foldersharing=<1|0>]
[,videostreaming=<off|all|filter>]
Configure additional enhancements for SPICE.

- `--sshkeys` <filepath>
cloud-init: Setup public SSH keys (one key per line, OpenSSH format).

- `--startdate` (now | YYYY-MM-DD | YYYY-MM-DDTHH:MM:SS) (default = now)
Set the initial date of the real time clock. Valid format for date are:’now’ or 2006-06-17T16:01:21 or
2006-06-17.

- `--startup` `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

- `--tablet` <boolean> (default = 1)
Enable/disable the USB tablet device.

- `--tags` <string>
Tags of the VM. This is only meta information.

- `--tdf` <boolean> (default = 0)
Enable/disable time drift fix.

- `--template` <boolean> (default = 0)
Enable/disable Template.

- `--tpmstate0` [file=]<volume> [,format=<raw|qcow2|vmdk>]
[,import-from=<source volume>] [,size=<DiskSize>]
[,version=<v1.2|v2.0>]
Configure a Disk for storing TPM state. The format is fixed to raw. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate a new volume. Note that SIZE_IN_GiB is ignored here and 4 MiB
will be used instead. Use STORAGE_ID:0 and the import-from parameter to import from an existing
volume.

--unused[n] [file=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

--usb[n] [[host=]<HOSTUSBDEVICE|spice>] [,mapping=<mapping-id>]
[,usb3=<1|0>]
Configure an USB device (n is 0 to 4, for machine version >= 7.1 and ostype l26 or windows > 7, n can
be up to 14).


- `--vcpus` <integer> (1 - N) (default = 0)
Number of hotplugged vcpus.

- `--vga` [[type=]<enum>] [,clipboard=<vnc>] [,memory=<integer>]
Configure the VGA hardware.

--virtio[n] [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,import-from=<source volume>] [,iops=<iops>] [,iops_max=<iops>]
[,iops_max_length=<seconds>] [,iops_rd=<iops>]
[,iops_rd_max=<iops>] [,iops_rd_max_length=<seconds>]
[,iops_wr=<iops>] [,iops_wr_max=<iops>]
[,iops_wr_max_length=<seconds>] [,iothread=<1|0>] [,mbps=<mbps>]
[,mbps_max=<mbps>] [,mbps_rd=<mbps>] [,mbps_rd_max=<mbps>]
[,mbps_wr=<mbps>] [,mbps_wr_max=<mbps>] [,media=<cdrom|disk>]
[,replicate=<1|0>] [,rerror=<ignore|report|stop>] [,ro=<1|0>]
[,serial=<serial>] [,shared=<1|0>] [,size=<DiskSize>]
[,snapshot=<1|0>] [,werror=<enum>]
Use volume as VIRTIO hard disk (n is 0 to 15). Use the special syntax STORAGE_ID:SIZE_IN_GiB to
allocate a new volume. Use STORAGE_ID:0 and the import-from parameter to import from an existing
volume.

--virtiofs[n] [dirid=]<mapping-id> [,cache=<enum>]
[,direct-io=<1|0>] [,expose-acl=<1|0>] [,expose-xattr=<1|0>]
Configuration for sharing a directory between host and guest using Virtio-fs.

- `--vmgenid` <UUID> (default = 1 (autogenerated))
Set VM Generation ID. Use 1 to autogenerate on create or update, pass 0 to disable explicitly.

- `--vmstatestorage` <storage ID>
Default storage for VM state volumes/files.

- `--watchdog` [[model=]<i6300esb|ib700>] [,action=<enum>]
Create a virtual hardware watchdog device.

```
qm showcmd <vmid> [OPTIONS]
```

Show command line which is used to start the VM (debug info).

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--pretty` <boolean> (default = 0)
Puts each option on a new line to enhance human readability


- `--snapshot` <string>
Fetch config values from given snapshot.

```
qm shutdown <vmid> [OPTIONS]
```

Shutdown virtual machine. This is similar to pressing the power button on a physical machine. This will send
an ACPI event for the guest OS, which should then proceed to a clean shutdown.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--forceStop` <boolean> (default = 0)
Make sure the VM stops.

- `--keepActive` <boolean> (default = 0)
Do not deactivate storage volumes.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

- `--timeout` <integer> (0 - N)
Wait maximal timeout seconds.

```
qm snapshot <vmid> <snapname> [OPTIONS]
```

Snapshot a VM.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<snapname>: <string>
The name of the snapshot.

- `--description` <string>
A textual description or comment.

- `--vmstate` <boolean>
Save the vmstate

```
qm start <vmid> [OPTIONS]
```

Start virtual machine.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.


- `--force-cpu` <string>
Override QEMU’s -cpu argument with the given string.

- `--machine` [[type=]<machine type>] [,aw-bits=<number>]
[,enable-s3=<1|0>] [,enable-s4=<1|0>] [,viommu=<intel|virtio>]
Specify the QEMU machine.

- `--migratedfrom` <string>
The cluster node name.

- `--migration_network` <string>
CIDR of the (sub) network that is used for migration.

- `--migration_type` <insecure | secure>
Migration traffic is encrypted using an SSH tunnel by default. On secure, completely private networks
this can be disabled to increase performance.

- `--nets-host-mtu` net\d+=\d+(,net\d+=\d+)*
Used for migration compat. List of VirtIO network devices and their effective host_mtu setting according to the QEMU object model on the source side of the migration. A value of 0 means that the
host_mtu parameter is to be avoided for the corresponding device.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

- `--stateuri` <string>
Some command save/restore state from this location.

- `--targetstorage` <string>
Mapping from source to target storages. Providing only a single storage ID maps all source storages
to that storage. Providing the special value 1 will map each source storage to itself.

- `--timeout` <integer> (0 - N) (default = max(30, vm memory in GiB))
Wait maximal timeout seconds.

- `--with-conntrack-state` <boolean> (default = 0)
Whether to migrate conntrack entries for running VMs.

```
qm status <vmid> [OPTIONS]
```

Show VM status.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--verbose` <boolean>
Verbose output format


```
qm stop <vmid> [OPTIONS]
```

Stop virtual machine. The qemu process will exit immediately. This is akin to pulling the power plug of a
running computer and may damage the VM data.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--keepActive` <boolean> (default = 0)
Do not deactivate storage volumes.

- `--migratedfrom` <string>
The cluster node name.

- `--overrule-shutdown` <boolean> (default = 0)
Try to abort active qmshutdown tasks before stopping.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

- `--timeout` <integer> (0 - N)
Wait maximal timeout seconds.

```
qm suspend <vmid> [OPTIONS]
```

Suspend virtual machine.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

- `--statestorage` <storage ID>
The storage for the VM state

> **Note:**
> Requires option(s): todisk


- `--todisk` <boolean> (default = 0)
If set, suspends the VM to disk. Will be resumed on next VM start.

```
qm template <vmid> [OPTIONS]
```

Create a Template.


<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--disk` <efidisk0 | ide0 | ide1 | ide2 | ide3 | sata0 | sata1 |
sata2 | sata3 | sata4 | sata5 | scsi0 | scsi1 | scsi10 | scsi11 |
scsi12 | scsi13 | scsi14 | scsi15 | scsi16 | scsi17 | scsi18 |
scsi19 | scsi2 | scsi20 | scsi21 | scsi22 | scsi23 | scsi24 |
scsi25 | scsi26 | scsi27 | scsi28 | scsi29 | scsi3 | scsi30 | scsi4
| scsi5 | scsi6 | scsi7 | scsi8 | scsi9 | tpmstate0 | virtio0 |
virtio1 | virtio10 | virtio11 | virtio12 | virtio13 | virtio14 |
virtio15 | virtio2 | virtio3 | virtio4 | virtio5 | virtio6 |
virtio7 | virtio8 | virtio9>
If you want to convert only 1 disk to base image.

```
qm terminal <vmid> [OPTIONS]
```

Open a terminal using a serial device (The VM need to have a serial device configured, for example serial0:
socket)

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--escape` <string> (default = ˆO)
Escape character.

- `--iface` <serial0 | serial1 | serial2 | serial3>
Select the serial device. By default we simply use the first suitable device.

```
qm unlink
```

An alias for qm disk unlink.

```
qm unlock <vmid>
```

Unlock the VM.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm vncproxy <vmid>
```

Proxy VM VNC traffic to stdin/stdout

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm wait <vmid> [OPTIONS]
```

Wait until the VM is stopped.

## See also


## See also

- [qm - QEMU/KVM VM Manager](qm.md)
- [qm commands: create options (cont.) through help](qm-create-help.md)
- [qm commands: import through listsnapshot](qm-import-listsnapshot.md)
- [qm commands: listsnapshot through set](qm-listsnapshot-set.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
