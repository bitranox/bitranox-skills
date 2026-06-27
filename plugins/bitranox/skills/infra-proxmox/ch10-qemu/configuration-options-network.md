# VM Configuration Options: TDX, Network and IDE

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

intel-tdx: [type=]<tdx-type> ,attestation=<1|0>
[,vsock-cid=<integer>] [,vsock-port=<integer>]
Trusted Domain Extension (TDX) features by Intel CPUs

attestation=<boolean> (default = 1)
Enable TDX attestation by including quote-generation-socket

type=<tdx-type>
Enable TDX

vsock-cid=<integer> (2 - N) (default = 2)
CID for vsock of Quote Generation Service


vsock-port=<integer> (0 - N) (default = 4050)
Port for vsock of Quote Generation Service

ipconfig[n]: [gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>]
[,ip=<IPv4Format/CIDR>] [,ip6=<IPv6Format/CIDR>]
cloud-init: Specify IP addresses and gateways for the corresponding interface.
IP addresses use CIDR notation, gateways are optional but need an IP of the same type specified.
The special string dhcp can be used for IP addresses to use DHCP, in which case no explicit gateway
should be provided. For IPv6 the special string auto can be used to use stateless autoconfiguration.
This requires cloud-init 19.4 or newer.
If cloud-init is enabled and neither an IPv4 nor an IPv6 address is specified, it defaults to using dhcp
on IPv4.

gw=<GatewayIPv4>
Default gateway for IPv4 traffic.

> **Note:**
> Requires option(s): ip


gw6=<GatewayIPv6>
Default gateway for IPv6 traffic.

> **Note:**
> Requires option(s): ip6


ip=<IPv4Format/CIDR> (default = dhcp)
IPv4 address in CIDR format.

ip6=<IPv6Format/CIDR> (default = dhcp)
IPv6 address in CIDR format.

ivshmem: size=<integer> [,name=<string>]
Inter-VM shared memory. Useful for direct communication between VMs, or to the host.

name=<string>
The name of the file. Will be prefixed with pve-shm-. Default is the VMID. Will be deleted when
the VM is stopped.

size=<integer> (1 - N)
The size of the file in MB.

keephugepages: <boolean> (default = 0)
Use together with hugepages. If enabled, hugepages will not not be deleted after VM shutdown and
can be used for subsequent starts.


keyboard: <da | de | de-ch | en-gb | en-us | es | fi | fr | fr-be |
fr-ca | fr-ch | hu | is | it | ja | lt | mk | nl | no | pl | pt |
pt-br | sl | sv | tr>
Keyboard layout for VNC server. This option is generally not required and is often better handled from
within the guest OS.

kvm: <boolean> (default = 1)
Enable/disable KVM hardware virtualization.

localtime: <boolean>
Set the real time clock (RTC) to local time. This is enabled by default if the ostype indicates a
Microsoft Windows OS.

lock: <backup | clone | create | migrate | rollback | snapshot |
snapshot-delete | suspended | suspending>
Lock/unlock the VM.

machine: [[type=]<machine type>] [,aw-bits=<number>]
[,enable-s3=<1|0>] [,enable-s4=<1|0>] [,viommu=<intel|virtio>]
Specify the QEMU machine.

aw-bits=<number> (32 - 64)
Specifies the vIOMMU address space bit width.
Intel vIOMMU supports a bit width of either 39 or 48 bits and VirtIO vIOMMU supports any bit
width between 32 and 64 bits.

enable-s3=<boolean>
Enables S3 power state. Defaults to false beginning with machine types 9.2+pve1, true before.

enable-s4=<boolean>
Enables S4 power state. Defaults to false beginning with machine types 9.2+pve1, true before.

type=<machine type>
Specifies the QEMU machine type.

viommu=<intel | virtio>
Enable and set guest vIOMMU variant (Intel vIOMMU needs q35 to be set as machine type).

memory: [current=]<integer>
Memory properties.

current=<integer> (16 - N) (default = 512)
Current amount of online RAM for the VM in MiB. This is the maximum available memory when
you use the balloon device.

migrate_downtime: <number> (0 - N) (default = 0.1)
Set maximum tolerated downtime (in seconds) for migrations. Should the migration not be able to


converge in the very end, because too much newly dirtied RAM needs to be transferred, the limit will
be increased automatically step-by-step until migration can converge.

migrate_speed: <integer> (0 - N) (default = 0)
Set maximum speed (in MB/s) for migrations. Value 0 is no limit.

name: <string>
Set a name for the VM. Only used on the configuration web interface.

nameserver: <string>
cloud-init: Sets DNS server IP address for a container. Create will automatically use the setting from
the host if neither searchdomain nor nameserver are set.

net[n]: [model=]<enum> [,bridge=<bridge>] [,firewall=<1|0>]
[,link_down=<1|0>] [,macaddr=<XX:XX:XX:XX:XX:XX>] [,mtu=<integer>]
[,queues=<integer>] [,rate=<number>] [,tag=<integer>]
[,trunks=<vlanid[;vlanid...]>] [,<model>=<macaddr>]
Specify network devices.

bridge=<bridge>
Bridge to attach the network device to. The Proxmox VE standard bridge is called vmbr0.
If you do not specify a bridge, we create a kvm user (NATed) network device, which provides
DHCP and DNS services. The following addresses are used:


#### 10.0.2.2 10.0.2.3


#### 10.0.2.4 Gateway

DNS Server
SMB Server

The DHCP server assign addresses to the guest starting from 10.0.2.15.

firewall=<boolean>
Whether this interface should be protected by the firewall.

link_down=<boolean>
Whether this interface should be disconnected (like pulling the plug).

macaddr=<XX:XX:XX:XX:XX:XX>
A common MAC address with the I/G (Individual/Group) bit not set.

model=<e1000 | e1000-82540em | e1000-82544gc | e1000-82545em |
e1000e | i82551 | i82557b | i82559er | ne2k_isa | ne2k_pci |
pcnet | rtl8139 | virtio | vmxnet3>
Network Card Model. The virtio model provides the best performance with very low CPU overhead. If your guest does not support this driver, it is usually best to use e1000.

mtu=<integer> (1 - 65520)
Force MTU of network device (VirtIO only). Setting to 1 or empty will use the bridge MTU

queues=<integer> (0 - 64)
Number of packet queues to be used on the device.


rate=<number> (0 - N)
Rate limit in mbps (megabytes per second) as floating point number.

tag=<integer> (1 - 4094)
VLAN tag to apply to packets on this interface.

trunks=<vlanid[;vlanid...]>
VLAN trunks to pass through this interface.

numa: <boolean> (default = 0)
Enable/disable NUMA.

numa[n]: cpus=<id[-id];...> [,hostnodes=<id[-id];...>]
[,memory=<number>] [,policy=<preferred|bind|interleave>]
NUMA topology.

cpus=<id[-id];...>
CPUs accessing this NUMA node.

hostnodes=<id[-id];...>
Host NUMA nodes to use.

memory=<number>
Amount of memory this NUMA node provides.

policy=<bind | interleave | preferred>
NUMA allocation policy.

onboot: <boolean> (default = 0)
Specifies whether a VM will be started during system bootup.

ostype: <l24 | l26 | other | solaris | w2k | w2k3 | w2k8 | win10 |
win11 | win7 | win8 | wvista | wxp> (default = other)
Specify guest operating system. This is used to enable special optimization/features for specific operating systems:
other
wxp
w2k
w2k3
w2k8
wvista
win7
win8
win10
win11
l24
l26

unspecified OS
Microsoft Windows XP
Microsoft Windows 2000
Microsoft Windows 2003
Microsoft Windows 2008
Microsoft Windows Vista
Microsoft Windows 7
Microsoft Windows 8/2012/2012r2
Microsoft Windows 10/2016/2019
Microsoft Windows 11/2022/2025
Linux 2.4 Kernel
Linux 2.6 - 6.X Kernel

solaris


Solaris/OpenSolaris/OpenIndiania kernel

parallel[n]: /dev/parport\d+|/dev/usb/lp\d+
Map host parallel devices (n is 0 to 2).

> **Note:**
> This option allows direct access to host hardware. So it is no longer possible to migrate such
> machines - use with special care.


> **Caution:**
> Experimental! User reported problems with this option.


protection: <boolean> (default = 0)
Sets the protection flag of the VM. This will disable the remove VM and remove disk operations.

reboot: <boolean> (default = 1)
Allow reboot. If set to 0 the VM exit on reboot.

rng0: [source=]</dev/urandom|/dev/random|/dev/hwrng>
[,max_bytes=<integer>] [,period=<integer>]
Configure a VirtIO-based Random Number Generator.

max_bytes=<integer> (default = 1024)
Maximum bytes of entropy allowed to get injected into the guest every period milliseconds. Use
0 to disable limiting (potentially dangerous!).

period=<integer> (default = 1000)
Every period milliseconds the entropy-injection quota is reset, allowing the guest to retrieve another max_bytes of entropy.

source=</dev/hwrng | /dev/random | /dev/urandom>
The file on the host to gather entropy from. Using urandom does not decrease security in any
meaningful way, as it’s still seeded from real entropy, and the bytes provided will most likely be
mixed with real entropy on the guest as well. /dev/hwrng can be used to pass through a hardware
RNG from the host.


sata[n]: [file=]<volume> [,aio=<native|threads|io_uring>]
[,backup=<1|0>] [,bps=<bps>] [,bps_max_length=<seconds>]
[,bps_rd=<bps>] [,bps_rd_max_length=<seconds>] [,bps_wr=<bps>]
[,bps_wr_max_length=<seconds>] [,cache=<enum>]
[,detect_zeroes=<1|0>] [,discard=<ignore|on>] [,format=<enum>]
[,iops=<iops>] [,iops_max=<iops>] [,iops_max_length=<seconds>]
[,iops_rd=<iops>] [,iops_rd_max=<iops>]
[,iops_rd_max_length=<seconds>] [,iops_wr=<iops>]
[,iops_wr_max=<iops>] [,iops_wr_max_length=<seconds>]
[,mbps=<mbps>] [,mbps_max=<mbps>] [,mbps_rd=<mbps>]
[,mbps_rd_max=<mbps>] [,mbps_wr=<mbps>] [,mbps_wr_max=<mbps>]
[,media=<cdrom|disk>] [,replicate=<1|0>]
[,rerror=<ignore|report|stop>] [,serial=<serial>] [,shared=<1|0>]
[,size=<DiskSize>] [,snapshot=<1|0>] [,ssd=<1|0>] [,werror=<enum>]
[,wwn=<wwn>]
Use volume as SATA hard disk or CD-ROM (n is 0 to 5).

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

werror=<enospc | ignore | report | stop>
Write error action.

wwn=<wwn>
The drive’s worldwide name, encoded as 16 bytes hex string, prefixed by 0x.


## See also

- [VM Configuration Options](configuration-options.md)
- [VM Configuration Options: SCSI, VirtIO and Misc](configuration-options-scsi-misc.md)
- [QEMU/KVM Overview](_index.md)
