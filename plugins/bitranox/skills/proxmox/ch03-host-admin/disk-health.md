# Disk Health Monitoring

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

The default port is set to 2003 and the default graphite path is proxmox.
By default, Proxmox VE sends the data over UDP, so the graphite server has to be configured to accept this.
Here the maximum transmission unit (MTU) can be configured for environments not using the standard 1500
MTU.
You can also configure the plugin to use TCP. In order not to block the important pvestatd statistic collection daemon, a timeout is required to cope with network problems.


### 3.6.2 Influxdb plugin configuration


Proxmox VE sends the data over UDP, so the influxdb server has to be configured for this. The MTU can
also be configured here, if necessary.
Here is an example configuration for influxdb (on your influxdb server):

[[udp]]
enabled = true
bind-address = "0.0.0.0:8089"
database = "proxmox"
batch-size = 1000
batch-timeout = "1s"
With this configuration, your server listens on all IP addresses on port 8089, and writes the data in the
proxmox database
Alternatively, the plugin can be configured to use the http(s) API of InfluxDB 2.x. InfluxDB 1.8.x does contain
a forwards compatible API endpoint for this v2 API.
To use it, set influxdbproto to http or https (depending on your configuration). By default, Proxmox VE uses
the organization proxmox and the bucket/db proxmox (They can be set with the configuration organization
and bucket respectively).
Since InfluxDB’s v2 API is only available with authentication, you have to generate a token that can write into
the correct bucket and set it.
In the v2 compatible API of 1.8.x, you can use user:password as token (if required), and can omit the
organization since that has no meaning in InfluxDB 1.x.
You can also set the HTTP Timeout (default is 1s) with the timeout setting, as well as the maximum batch
size (default 25000000 bytes) with the max-body-size setting (this corresponds to the InfluxDB setting with
the same name).


## 3.7 Disk Health Monitoring


Although a robust and redundant storage is recommended, it can be very helpful to monitor the health of
your local disks.


Starting with Proxmox VE 4.3, the package smartmontools 1 is installed and required. This is a set of tools
to monitor and control the S.M.A.R.T. system for local hard disks.
You can get the status of a disk by issuing the following command:

# smartctl -a /dev/sdX
where /dev/sdX is the path to one of your local disks.
If the output says:

SMART support is: Disabled
you can enable it with the command:

# smartctl -s on /dev/sdX
For more information on how to use smartctl, please see man smartctl.
By default, the smartmontools daemon smartd is active and enabled, and scans any devices matching

- /dev/sd[a-z]
- /dev/sd[a-z][a-z]
- /dev/hd[a-t]
- or /dev/nvme[0-99]
every 30 minutes for errors and warnings, and sends an e-mail to root if it detects a problem.
For more information about how to configure smartd, please see man smartd and man smartd.conf.
If you use your hard disks with a hardware raid controller, there are most likely tools to monitor the disks in
the raid array and the array itself. For more information about this, please refer to the vendor of your raid
controller.


## 3.8 Logical Volume Manager (LVM)


Most people install Proxmox VE directly on a local disk. The Proxmox VE installation CD offers several
options for local disk management, and the current default setup uses LVM. The installer lets you select a
single disk for such setup, and uses that disk as physical volume for the Volume Group (VG) pve. The
following output is from a test installation using a small 8GB disk:

# pvs
PV
/dev/sda3

```
# vgs
VG
pve
```


VG
pve

Fmt Attr PSize PFree
lvm2 a-- 7.87g 876.00m

#PV #LV #SN Attr
VSize VFree
1
3
0 wz--n- 7.87g 876.00m

The installer allocates three Logical Volumes (LV) inside this VG:
1 smartmontools homepage https://www.smartmontools.org
