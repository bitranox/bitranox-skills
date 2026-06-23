# qm - QEMU/KVM VM Manager

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

A.9


```
qm - QEMU/KVM Virtual Machine Manager
```


```
qm <COMMAND> [ARGS] [OPTIONS]
```


```
qm agent
```

An alias for qm guest cmd.

```
qm cleanup <vmid> <clean-shutdown> <guest-requested>
```

Cleans up resources like tap devices, vgpus, etc. Called after a vm shuts down, crashes, etc.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<clean-shutdown>: <boolean>
Indicates if qemu shutdown cleanly.

<guest-requested>: <boolean>
Indicates if the shutdown was requested by the guest or via qmp.

```
qm clone <vmid> <newid> [OPTIONS]
```

Create a copy of virtual machine/template.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<newid>: <integer> (100 - 999999999)
VMID for the clone.

- `--bwlimit` <integer> (0 - N) (default = clone limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--description` <string>
Description for the new VM.

- `--format` <qcow2 | raw | vmdk>
Target format for file storage. Only valid for full clone.

- `--full` <boolean>
Create a full copy of all disks. This is always done when you clone a normal VM. For VM templates,
we try to create a linked clone by default.

- `--name` <string>
Set a name for the new VM.


- `--pool` <string>
Add the new VM to the specified pool.

- `--snapname` <string>
The name of the snapshot.

- `--storage` <storage ID>
Target storage for full clone.

- `--target` <string>
Target node. Only allowed if the original VM is on shared storage.

```
qm cloudinit dump <vmid> <type>
```

Get automatically generated cloudinit config.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<type>: <meta | network | user>
Config type.

```
qm cloudinit pending <vmid>
```

Get the cloudinit configuration with both current and pending values.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm cloudinit update <vmid>
```

Regenerate and change cloudinit config drive.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

```
qm config <vmid> [OPTIONS]
```

Get the virtual machine configuration with pending configuration changes applied. Set the current parameter
to get the current configuration instead.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--current` <boolean> (default = 0)
Get current values (instead of pending values).


- `--snapshot` <string>
Fetch config values from given snapshot.

```
qm create <vmid> [OPTIONS]
```

Create or restore a virtual machine.

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

- `--archive` <string>
The backup archive. Either the file system path to a .tar or .vma file (use - to pipe data from stdin) or
a proxmox storage backup volume identifier.

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

- `--bwlimit` <integer> (0 - N) (default = restore limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

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

- `--description` <string>
Description for the VM. Shown in the web-interface VM’s summary. This is saved as comment inside
the configuration file.

- `--efidisk0` [file=]<volume> [,efitype=<2m|4m>] [,format=<enum>]
[,import-from=<source volume>] [,ms-cert=<2011|2023>]
[,pre-enrolled-keys=<1|0>] [,size=<DiskSize>]
Configure a disk for storing EFI vars. Use the special syntax STORAGE_ID:SIZE_IN_GiB to allocate
a new volume. Note that SIZE_IN_GiB is ignored here and that the default EFI vars are copied to
the volume instead. Use STORAGE_ID:0 and the import-from parameter to import from an existing
volume.

- `--force` <boolean>
Allow to overwrite existing VM.

> **Note:**
> Requires option(s): archive


- `--freeze` <boolean>
Freeze CPU at startup (use c monitor command to start execution).

- `--ha-managed` <boolean> (default = 0)
Add the VM as a HA resource after it was created.

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

- `--import-working-storage` <storage ID>
A file-based storage with images content-type enabled, which is used as an intermediary extraction
storage during import. Defaults to the source storage.

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

- `--live-restore` <boolean>
Start the VM immediately while importing or restoring in the background.

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

- `--pool` <string>
Add the VM to the specified pool.

- `--protection` <boolean> (default = 0)
Sets the protection flag of the VM. This will disable the remove VM and remove disk operations.

- `--reboot` <boolean> (default = 1)
Allow reboot. If set to 0 the VM exit on reboot.

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

- `--start` <boolean> (default = 0)
Start VM after it was created successfully.

- `--startdate` (now | YYYY-MM-DD | YYYY-MM-DDTHH:MM:SS) (default = now)
Set the initial date of the real time clock. Valid format for date are:’now’ or 2006-06-17T16:01:21 or
2006-06-17.

- `--startup` `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

- `--storage` <storage ID>
Default storage.

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

- `--unique` <boolean>
Assign a unique random ethernet address.

> **Note:**
> Requires option(s): archive


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

## See also

- [qm commands: create options (cont.) through help](qm-create-help.md)
- [qm commands: import through listsnapshot](qm-import-listsnapshot.md)
- [qm commands: listsnapshot through set](qm-listsnapshot-set.md)
- [qm commands: set (cont.) through wait](qm-set-wait.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
