# VM Configuration Options: SCSI, VirtIO and Miscellaneous

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

scsi[n]: [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,iops=<iops>] [,iops_max=<iops>] [,iops_max_length=<seconds>]
[,iops_rd=<iops>] [,iops_rd_max=<iops>]
[,iops_rd_max_length=<seconds>] [,iops_wr=<iops>]
[,iops_wr_max=<iops>] [,iops_wr_max_length=<seconds>]
[,iothread=<1|0>] [,mbps=<mbps>] [,mbps_max=<mbps>]
[,mbps_rd=<mbps>] [,mbps_rd_max=<mbps>] [,mbps_wr=<mbps>]
[,mbps_wr_max=<mbps>] [,media=<cdrom|disk>] [,product=<product>]
[,queues=<integer>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,ro=<1|0>] [,scsiblock=<1|0>]
[,serial=<serial>] [,shared=<1|0>] [,size=<DiskSize>]
[,snapshot=<1|0>] [,ssd=<1|0>] [,vendor=<vendor>] [,werror=<enum>]
[,wwn=<wwn>]
Use volume as SCSI hard disk or CD-ROM (n is 0 to 30).


aio=<io_uring | native | threads>
AIO type to use.

backup=<boolean>
Whether the drive should be included when making backups.

bps=<bps>
Maximum r/w speed in bytes per second.

bps_max_length=<seconds>
Maximum length of I/O bursts in seconds.

bps_rd=<bps>
Maximum read speed in bytes per second.

bps_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

bps_wr=<bps>
Maximum write speed in bytes per second.

bps_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

cache=<directsync | none | unsafe | writeback | writethrough>
The drive’s cache mode

detect_zeroes=<boolean>
Controls whether to detect and try to optimize writes of zeroes.

discard=<ignore | on>
Controls whether to pass discard/trim requests to the underlying storage.

file=<volume>
The drive’s backing volume.

format=<cloop | qcow | qcow2 | qed | raw | vmdk>
The drive’s backing file’s data format.

iops=<iops>
Maximum r/w I/O in operations per second.

iops_max=<iops>
Maximum unthrottled r/w I/O pool in operations per second.

iops_max_length=<seconds>
Maximum length of I/O bursts in seconds.

iops_rd=<iops>
Maximum read I/O in operations per second.

iops_rd_max=<iops>
Maximum unthrottled read I/O pool in operations per second.


iops_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

iops_wr=<iops>
Maximum write I/O in operations per second.

iops_wr_max=<iops>
Maximum unthrottled write I/O pool in operations per second.

iops_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

iothread=<boolean>
Whether to use iothreads for this drive

mbps=<mbps>
Maximum r/w speed in megabytes per second.

mbps_max=<mbps>
Maximum unthrottled r/w pool in megabytes per second.

mbps_rd=<mbps>
Maximum read speed in megabytes per second.

mbps_rd_max=<mbps>
Maximum unthrottled read pool in megabytes per second.

mbps_wr=<mbps>
Maximum write speed in megabytes per second.

mbps_wr_max=<mbps>
Maximum unthrottled write pool in megabytes per second.

media=<cdrom | disk> (default = disk)
The drive’s media type.

product=<product>
The drive’s product name, up to 16 bytes long.

queues=<integer> (2 - N)
Number of queues.

replicate=<boolean> (default = 1)
Whether the drive should considered for replication jobs.

rerror=<ignore | report | stop>
Read error action.

ro=<boolean>
Whether the drive is read-only.

scsiblock=<boolean> (default = 0)
whether to use scsi-block for full passthrough of host block device


> **Warning:**
> can lead to I/O errors in combination with low memory or high memory fragmentation
> on host


serial=<serial>
The drive’s reported serial number, url-encoded, up to 20 bytes long.

shared=<boolean> (default = 0)
Mark this locally-managed volume as available on all nodes.


> **Warning:**
> This option does not share the volume automatically, it assumes it is shared already!


size=<DiskSize>
Disk size. This is purely informational and has no effect.

snapshot=<boolean>
Controls qemu’s snapshot mode feature. If activated, changes made to the disk are temporary
and will be discarded when the VM is shutdown.

ssd=<boolean>
Whether to expose this drive as an SSD, rather than a rotational hard disk.

vendor=<vendor>
The drive’s vendor name, up to 8 bytes long.

werror=<enospc | ignore | report | stop>
Write error action.

wwn=<wwn>
The drive’s worldwide name, encoded as 16 bytes hex string, prefixed by 0x.

scsihw: <lsi | lsi53c810 | megasas | pvscsi | virtio-scsi-pci |
virtio-scsi-single> (default = lsi)
SCSI controller model

searchdomain: <string>
cloud-init: Sets DNS search domains for a container. Create will automatically use the setting from the
host if neither searchdomain nor nameserver are set.

serial[n]: (/dev/.+|socket)
Create a serial device inside the VM (n is 0 to 3), and pass through a host serial device (i.e. /dev/ttyS0),
or create a unix socket on the host side (use qm terminal to open a terminal connection).

> **Note:**
> If you pass through a host serial device, it is no longer possible to migrate such machines - use with
> special care.


> **Caution:**
> Experimental! User reported problems with this option.


shares: <integer> (0 - 50000) (default = 1000)
Amount of memory shares for auto-ballooning. The larger the number is, the more memory this VM
gets. Number is relative to weights of all other running VMs. Using zero disables auto-ballooning.
Auto-ballooning is done by pvestatd.

smbios1: [base64=<1|0>] [,family=<Base64 encoded string>]
[,manufacturer=<Base64 encoded string>] [,product=<Base64 encoded
string>] [,serial=<Base64 encoded string>] [,sku=<Base64 encoded
string>] [,uuid=<UUID>] [,version=<Base64 encoded string>]
Specify SMBIOS type 1 fields.

base64=<boolean>
Flag to indicate that the SMBIOS values are base64 encoded

family=<Base64 encoded string>
Set SMBIOS1 family string.

manufacturer=<Base64 encoded string>
Set SMBIOS1 manufacturer.

product=<Base64 encoded string>
Set SMBIOS1 product ID.

serial=<Base64 encoded string>
Set SMBIOS1 serial number.

sku=<Base64 encoded string>
Set SMBIOS1 SKU string.

uuid=<UUID>
Set SMBIOS1 UUID.

version=<Base64 encoded string>
Set SMBIOS1 version.

smp: <integer> (1 - N) (default = 1)
The number of CPUs. Please use option -sockets instead.

sockets: <integer> (1 - N) (default = 1)
The number of CPU sockets.

spice_enhancements: [foldersharing=<1|0>]
[,videostreaming=<off|all|filter>]
Configure additional enhancements for SPICE.


foldersharing=<boolean> (default = 0)
Enable folder sharing via SPICE. Needs Spice-WebDAV daemon installed in the VM.

videostreaming=<all | filter | off> (default = off)
Enable video streaming. Uses compression for detected video streams.

sshkeys: <string>
cloud-init: Setup public SSH keys (one key per line, OpenSSH format).

startdate: (now | YYYY-MM-DD | YYYY-MM-DDTHH:MM:SS) (default = now)
Set the initial date of the real time clock. Valid format for date are:’now’ or 2006-06-17T16:01:21 or
2006-06-17.

startup: `[[order=]\d+] [,up=\d+] [,down=\d+] `
Startup and shutdown behavior. Order is a non-negative number defining the general startup order.
Shutdown in done with reverse ordering. Additionally you can set the up or down delay in seconds,
which specifies a delay to wait before the next VM is started or stopped.

tablet: <boolean> (default = 1)
Enable/disable the USB tablet device. This device is usually needed to allow absolute mouse positioning with VNC. Else the mouse runs out of sync with normal VNC clients. If you’re running lots of
console-only guests on one host, you may consider disabling this to save some context switches. This
is turned off by default if you use spice (qm set <vmid> --vga qxl).

tags: <string>
Tags of the VM. This is only meta information.

tdf: <boolean> (default = 0)
Enable/disable time drift fix.

template: <boolean> (default = 0)
Enable/disable Template.

tpmstate0: [file=]<volume> [,format=<raw|qcow2|vmdk>]
[,size=<DiskSize>] [,version=<v1.2|v2.0>]
Configure a Disk for storing TPM state. The format is fixed to raw.

file=<volume>
The drive’s backing volume.

format=<qcow2 | raw | vmdk>
Format of the image.

size=<DiskSize>
Disk size. This is purely informational and has no effect.


version=<v1.2 | v2.0> (default = v1.2)
The TPM interface version. v2.0 is newer and should be preferred. Note that this cannot be
changed later on.

unused[n]: [file=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

file=<volume>
The drive’s backing volume.

usb[n]: [[host=]<HOSTUSBDEVICE|spice>] [,mapping=<mapping-id>]
[,usb3=<1|0>]
Configure an USB device (n is 0 to 4, for machine version >= 7.1 and ostype l26 or windows > 7, n can
be up to 14).

host=<HOSTUSBDEVICE|spice>
The Host USB device or port or the value spice. HOSTUSBDEVICE syntax is:

'bus-port(.port)*' (decimal numbers) or
'vendor_id:product_id' (hexadecimal numbers) or
'spice'
You can use the lsusb -t command to list existing usb devices.

> **Note:**
> This option allows direct access to host hardware. So it is no longer possible to migrate such
> machines - use with special care.
> The value spice can be used to add a usb redirection devices for spice.
> Either this or the mapping key must be set.


mapping=<mapping-id>
The ID of a cluster wide mapping. Either this or the default-key host must be set.

usb3=<boolean> (default = 0)
Specifies whether if given host option is a USB3 device or port. For modern guests (machine
version >= 7.1 and ostype l26 and windows > 7), this flag is irrelevant (all devices are plugged
into a xhci controller).

vcpus: <integer> (1 - N) (default = 0)
Number of hotplugged vcpus.

vga: [[type=]<enum>] [,clipboard=<vnc>] [,memory=<integer>]
Configure the VGA Hardware. If you want to use high resolution modes (>= 1280x1024x16) you may
need to increase the vga memory option. Since QEMU 2.9 the default VGA display type is std for all
OS types besides some Windows versions (XP and older) which use cirrus. The qxl option enables
the SPICE display server. For win* OS you can select how many independent displays you want, Linux
guests can add displays them self. You can also run without any graphic card, using a serial device as
terminal.


clipboard=<vnc>
Enable a specific clipboard. If not set, depending on the display type the SPICE one will be
added. Migration with VNC clipboard is not yet supported!

memory=<integer> (4 - 512)
Sets the VGA memory (in MiB). Has no effect with serial display.

type=<cirrus | none | qxl | qxl2 | qxl3 | qxl4 | serial0 |
serial1 | serial2 | serial3 | std | virtio | virtio-gl |
vmware> (default = std)
Select the VGA type. Using type cirrus is not recommended.

virtio[n]: [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,iops=<iops>] [,iops_max=<iops>] [,iops_max_length=<seconds>]
[,iops_rd=<iops>] [,iops_rd_max=<iops>]
[,iops_rd_max_length=<seconds>] [,iops_wr=<iops>]
[,iops_wr_max=<iops>] [,iops_wr_max_length=<seconds>]
[,iothread=<1|0>] [,mbps=<mbps>] [,mbps_max=<mbps>]
[,mbps_rd=<mbps>] [,mbps_rd_max=<mbps>] [,mbps_wr=<mbps>]
[,mbps_wr_max=<mbps>] [,media=<cdrom|disk>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,ro=<1|0>] [,serial=<serial>]
[,shared=<1|0>] [,size=<DiskSize>] [,snapshot=<1|0>]
[,werror=<enum>]
Use volume as VIRTIO hard disk (n is 0 to 15).

aio=<io_uring | native | threads>
AIO type to use.

backup=<boolean>
Whether the drive should be included when making backups.

bps=<bps>
Maximum r/w speed in bytes per second.

bps_max_length=<seconds>
Maximum length of I/O bursts in seconds.

bps_rd=<bps>
Maximum read speed in bytes per second.

bps_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

bps_wr=<bps>
Maximum write speed in bytes per second.


bps_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

cache=<directsync | none | unsafe | writeback | writethrough>
The drive’s cache mode

detect_zeroes=<boolean>
Controls whether to detect and try to optimize writes of zeroes.

discard=<ignore | on>
Controls whether to pass discard/trim requests to the underlying storage.

file=<volume>
The drive’s backing volume.

format=<cloop | qcow | qcow2 | qed | raw | vmdk>
The drive’s backing file’s data format.

iops=<iops>
Maximum r/w I/O in operations per second.

iops_max=<iops>
Maximum unthrottled r/w I/O pool in operations per second.

iops_max_length=<seconds>
Maximum length of I/O bursts in seconds.

iops_rd=<iops>
Maximum read I/O in operations per second.

iops_rd_max=<iops>
Maximum unthrottled read I/O pool in operations per second.

iops_rd_max_length=<seconds>
Maximum length of read I/O bursts in seconds.

iops_wr=<iops>
Maximum write I/O in operations per second.

iops_wr_max=<iops>
Maximum unthrottled write I/O pool in operations per second.

iops_wr_max_length=<seconds>
Maximum length of write I/O bursts in seconds.

iothread=<boolean>
Whether to use iothreads for this drive

mbps=<mbps>
Maximum r/w speed in megabytes per second.

mbps_max=<mbps>
Maximum unthrottled r/w pool in megabytes per second.


mbps_rd=<mbps>
Maximum read speed in megabytes per second.

mbps_rd_max=<mbps>
Maximum unthrottled read pool in megabytes per second.

mbps_wr=<mbps>
Maximum write speed in megabytes per second.

mbps_wr_max=<mbps>
Maximum unthrottled write pool in megabytes per second.

media=<cdrom | disk> (default = disk)
The drive’s media type.

replicate=<boolean> (default = 1)
Whether the drive should considered for replication jobs.

rerror=<ignore | report | stop>
Read error action.

ro=<boolean>
Whether the drive is read-only.

serial=<serial>
The drive’s reported serial number, url-encoded, up to 20 bytes long.

shared=<boolean> (default = 0)
Mark this locally-managed volume as available on all nodes.


> **Warning:**
> This option does not share the volume automatically, it assumes it is shared already!


size=<DiskSize>
Disk size. This is purely informational and has no effect.

snapshot=<boolean>
Controls qemu’s snapshot mode feature. If activated, changes made to the disk are temporary
and will be discarded when the VM is shutdown.

werror=<enospc | ignore | report | stop>
Write error action.

virtiofs[n]: [dirid=]<mapping-id> [,cache=<enum>] [,direct-io=<1|0>]
[,expose-acl=<1|0>] [,expose-xattr=<1|0>]
Configuration for sharing a directory between host and guest using Virtio-fs.

cache=<always | auto | metadata | never> (default = auto)
The caching policy the file system should use (auto, always, metadata, never).


direct-io=<boolean> (default = 0)
Honor the O_DIRECT flag passed down by guest applications.

dirid=<mapping-id>
Mapping identifier of the directory mapping to be shared with the guest. Also used as a mount
tag inside the VM.

expose-acl=<boolean> (default = 0)
Enable support for POSIX ACLs (enabled ACL implies xattr) for this mount.

expose-xattr=<boolean> (default = 0)
Enable support for extended attributes for this mount.

vmgenid: <UUID> (default = 1 (autogenerated))
The VM generation ID (vmgenid) device exposes a 128-bit integer value identifier to the guest OS. This
allows to notify the guest operating system when the virtual machine is executed with a different configuration (e.g. snapshot execution or creation from a template). The guest operating system notices
the change, and is then able to react as appropriate by marking its copies of distributed databases as
dirty, re-initializing its random number generator, etc. Note that auto-creation only works when done
through API/CLI create or update methods, but not when manually editing the config file.

vmstatestorage: <storage ID>
Default storage for VM state volumes/files.

watchdog: [[model=]<i6300esb|ib700>] [,action=<enum>]
Create a virtual hardware watchdog device. Once enabled (by a guest action), the watchdog must be
periodically polled by an agent inside the guest or else the watchdog will reset the guest (or execute
the respective action specified)

action=<debug | none | pause | poweroff | reset | shutdown>
The action to perform if after activation the guest fails to poll the watchdog in time.

model=<i6300esb | ib700> (default = i6300esb)
Watchdog type to emulate.


## 10.15 Locks


Online migrations, snapshots and backups (vzdump) set a lock to prevent incompatible concurrent actions
on the affected VMs. Sometimes you need to remove such a lock manually (for example after a power
failure).


```
# qm unlock <vmid>
```


> **Caution:**
> Only do that if you are sure the action which set the lock is no longer running.


## See also

- [VM Configuration Options](configuration-options.md)
- [VM Configuration Options: TDX, Network and IDE](configuration-options-network.md)
- [QEMU/KVM Overview](_index.md)
