# qm commands: listsnapshot through set

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

qm listsnapshot <vmid>
```

List all snapshots.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm migrate <vmid> <target> [OPTIONS]
```

Migrate virtual machine. Creates a new migration task.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<target>: <string>
Target node.

- `--bwlimit` <integer> (0 - N) (default = migrate limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--force` <boolean>
Allow to migrate VMs which use local devices. Only root may use this option.

- `--migration_network` <string>
CIDR of the (sub) network that is used for migration.


- `--migration_type` <insecure | secure>
Migration traffic is encrypted using an SSH tunnel by default. On secure, completely private networks
this can be disabled to increase performance.

- `--online` <boolean>
Use online/live migration if VM is running. Ignored if VM is stopped.

- `--targetstorage` <string>
Mapping from source to target storages. Providing only a single storage ID maps all source storages
to that storage. Providing the special value 1 will map each source storage to itself.

- `--with-conntrack-state` <boolean> (default = 0)
Whether to migrate conntrack entries for running VMs.

- `--with-local-disks` <boolean>
Enable live storage migration for local disk

```
qm monitor <vmid>
```

Enter QEMU Monitor interface.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm move-disk
```

An alias for qm disk move.

```
qm move_disk
```

An alias for qm disk move.

```
qm mtunnel
```

Used by qmigrate - do not use manually.

```
qm nbdstop <vmid>
```

Stop embedded nbd server.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm pending <vmid>
```

Get the virtual machine configuration with both current and pending values.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.


```
qm reboot <vmid> [OPTIONS]
```

Reboot the VM by shutting it down, and starting it again. Applies pending changes.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--timeout` <integer> (0 - N)
Wait maximal timeout seconds for the shutdown.


```
qm remote-migrate <vmid> [<target-vmid>] <target-endpoint> --target-bridge <stri
```


- `--target-storage` <string> [OPTIONS]
Migrate virtual machine to a remote cluster. Creates a new migration task. EXPERIMENTAL feature!

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<target-vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<target-endpoint>: apitoken=<PVEAPIToken=user@realm!token=SECRET>
,host=<ADDRESS> [,fingerprint=<FINGERPRINT>] [,port=<PORT>]
Remote target endpoint

- `--bwlimit` <integer> (0 - N) (default = migrate limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--delete` <boolean> (default = 0)
Delete the original VM and related data after successful migration. By default the original VM is kept
on the source cluster in a stopped state.

- `--online` <boolean>
Use online/live migration if VM is running. Ignored if VM is stopped.

- `--target-bridge` <string>
Mapping from source to target bridges. Providing only a single bridge ID maps all source bridges to
that bridge. Providing the special value 1 will map each source bridge to itself.

- `--target-storage` <string>
Mapping from source to target storages. Providing only a single storage ID maps all source storages
to that storage. Providing the special value 1 will map each source storage to itself.

```
qm rescan
```

An alias for qm disk rescan.

```
qm reset <vmid> [OPTIONS]
```

Reset virtual machine.


<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

```
qm resize
```

An alias for qm disk resize.

```
qm resume <vmid> [OPTIONS]
```

Resume virtual machine.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--nocheck` <boolean>
no description available

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.

```
qm rollback <vmid> <snapname> [OPTIONS]
```

Rollback VM state to specified snapshot.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<snapname>: <string>
The name of the snapshot.

- `--start` <boolean> (default = 0)
Whether the VM should get started after rolling back successfully. (Note: VMs will be automatically
started if the snapshot includes RAM.)

```
qm sendkey <vmid> <key> [OPTIONS]
```

Send key event to virtual machine.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<key>: <string>
The key (qemu monitor encoding).

- `--skiplock` <boolean>
Ignore locks - only root is allowed to use this option.


```
qm set <vmid> [OPTIONS]
```

Set virtual machine options (synchronous API) - You should consider using the POST method instead for
any actions involving hotplug or storage allocation.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--acpi` <boolean> (default = 1)
Enable/disable ACPI.

- `--affinity` <string>
List of host cores used to execute guest processes, for example: 0,5,8-11

- `--agent` [enabled=]<1|0> [,freeze-fs-on-backup=<1|0>]
[,fstrim_cloned_disks=<1|0>] [,type=<virtio|isa>]
Enable/disable communication with the QEMU Guest Agent and its properties.

- `--allow-ksm` <boolean> (default = 1)
Allow memory pages of this guest to be merged via KSM (Kernel Samepage Merging).

- `--amd-sev` [type=]<sev-type> [,allow-smt=<1|0>]
[,kernel-hashes=<1|0>] [,no-debug=<1|0>] [,no-key-sharing=<1|0>]
Secure Encrypted Virtualization (SEV) features by AMD CPUs

- `--arch` <aarch64 | x86_64>
Virtual processor architecture. Defaults to the host.

- `--args` <string>
Arbitrary arguments passed to kvm.

- `--audio0` device=<ich9-intel-hda|intel-hda|AC97>
[,driver=<spice|none>]
Configure a audio device, useful in combination with QXL/Spice.

- `--autostart` <boolean> (default = 0)
Automatic restart after crash (currently ignored).

- `--balloon` <integer> (0 - N)
Amount of target RAM for the VM in MiB. Using zero disables the ballon driver.

- `--bios` <ovmf | seabios> (default = seabios)
Select BIOS implementation.

- `--boot` [[legacy=]<[acdn]{1,4}>] [,order=<device[;device...]>]
Specify guest boot order. Use the order= sub-property as usage with no key or legacy= is deprecated.


- `--bootdisk` (ide|sata|scsi|virtio)\d+
Enable booting from specified disk. Deprecated: Use boot: order=foo;bar instead.

- `--cdrom` <volume>
This is an alias for option -ide2

- `--cicustom` [meta=<volume>] [,network=<volume>] [,user=<volume>]
[,vendor=<volume>]
cloud-init: Specify custom files to replace the automatically generated ones at start.

- `--cipassword` <password>
cloud-init: Password to assign the user. Using this is generally not recommended. Use ssh keys
instead. Also note that older cloud-init versions do not support hashed passwords.

- `--citype` <configdrive2 | nocloud | opennebula>
Specifies the cloud-init configuration format. The default depends on the configured operating system
type (ostype. We use the nocloud format for Linux, and configdrive2 for windows.

- `--ciupgrade` <boolean> (default = 1)
cloud-init: do an automatic package upgrade after the first boot.

- `--ciuser` <string>
cloud-init: User name to change ssh keys and password for instead of the image’s configured default
user.

- `--cores` <integer> (1 - N) (default = 1)
The number of cores per socket.

- `--cpu` [[cputype=]<string>] [,flags=<+FLAG[;-FLAG...]>]
[,guest-phys-bits=<integer>] [,hidden=<1|0>]
[,hv-vendor-id=<vendor-id>] [,phys-bits=<8-64|host>]
[,reported-model=<enum>]
Emulated CPU type.

- `--cpulimit` <number> (0 - 128) (default = 0)
Limit of CPU usage.

- `--cpuunits` <integer> (1 - 262144) (default = cgroup v1:
v2: 100)

1024, cgroup

CPU weight for a VM, will be clamped to [1, 10000] in cgroup v2.

- `--delete` <string>
A list of settings you want to delete.

- `--description` <string>
Description for the VM. Shown in the web-interface VM’s summary. This is saved as comment inside
the configuration file.


- `--digest` <string>
Prevent changes if current configuration file has different SHA1 digest. This can be used to prevent
concurrent modifications.

- `--efidisk0` [file=]<volume> [,efitype=<2m|4m>] [,format=<enum>]
[,import-from=<source volume>] [,ms-cert=<2011|2023>]
[,pre-enrolled-keys=<1|0>] [,size=<DiskSize>]
Configure a disk for storing EFI vars. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate
a new volume. Note that SIZE_IN_GiB is ignored here and that the default EFI vars are copied to
the volume instead. Use STORAGE_ID:0 and the import-from parameter to import from an existing
volume.

- `--force` <boolean>
Force physical removal. Without this, we simple remove the disk from the config file and create an
additional configuration entry called unused[n], which contains the volume ID. Unlink of unused[n]
always cause physical removal.

> **Note:**
> Requires option(s): delete


- `--freeze` <boolean>
Freeze CPU at startup (use c monitor command to start execution).

- `--hookscript` <string>
Script that will be executed during various steps in the vms lifetime.

--hostpci[n] [[host=]<HOSTPCIID[;HOSTPCIID2...]>] [,device-id=<hex
id>] [,driver=<vfio|keep>] [,legacy-igd=<1|0>]
[,mapping=<mapping-id>] [,mdev=<string>] [,pcie=<1|0>]
[,rombar=<1|0>] [,romfile=<string>] [,sub-device-id=<hex id>]
[,sub-vendor-id=<hex id>] [,vendor-id=<hex id>] [,x-vga=<1|0>]
Map host PCI devices into guest.

- `--hotplug` <string> (default = network,disk,usb)
Selectively enable hotplug features. This is a comma separated list of hotplug features: network, disk,
cpu, memory, usb and cloudinit. Use 0 to disable hotplug completely. Using 1 as value is an alias for
the default network,disk,usb. USB hotplugging is possible for guests with machine version >=

## 7.1 and ostype l26 or windows > 7.


- `--hugepages` <1024 | 2 | any>
Enables hugepages memory.
Sets the size of hugepages in MiB. If the value is set to any then 1 GiB hugepages will be used if
possible, otherwise the size will fall back to 2 MiB.


--ide[n] [file=]<volume> [,aio=<native|threads|io_uring>]
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
[,mbps_wr_max=<mbps>] [,media=<cdrom|disk>] [,model=<model>]
[,replicate=<1|0>] [,rerror=<ignore|report|stop>]
[,serial=<serial>] [,shared=<1|0>] [,size=<DiskSize>]
[,snapshot=<1|0>] [,ssd=<1|0>] [,werror=<enum>] [,wwn=<wwn>]
Use volume as IDE hard disk or CD-ROM (n is 0 to 3). Use the special syntax STORAGE_ID:SIZE_IN_GiB
to allocate a new volume. Use STORAGE_ID:0 and the import-from parameter to import from an existing volume.

- `--intel-tdx` [type=]<tdx-type> ,attestation=<1|0>
[,vsock-cid=<integer>] [,vsock-port=<integer>]
Trusted Domain Extension (TDX) features by Intel CPUs

--ipconfig[n] [gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>]
[,ip=<IPv4Format/CIDR>] [,ip6=<IPv6Format/CIDR>]
cloud-init: Specify IP addresses and gateways for the corresponding interface.
IP addresses use CIDR notation, gateways are optional but need an IP of the same type specified.
The special string dhcp can be used for IP addresses to use DHCP, in which case no explicit gateway
should be provided. For IPv6 the special string auto can be used to use stateless autoconfiguration.
This requires cloud-init 19.4 or newer.

## See also

- [qm - QEMU/KVM VM Manager](qm.md)
- [qm commands: create options (cont.) through help](qm-create-help.md)
- [qm commands: import through listsnapshot](qm-import-listsnapshot.md)
- [qm commands: set (cont.) through wait](qm-set-wait.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
