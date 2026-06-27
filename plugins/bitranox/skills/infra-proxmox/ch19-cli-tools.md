# Useful Command-line Tools

*[Main Index](SKILL.md)*

19.1


```
pvesubscription - Subscription Management
```


This tool is used to handle Proxmox VE subscriptions.

19.2


```
pveperf - Proxmox VE Benchmark Script
```


Tries to gather some CPU/hard disk performance data on the hard disk mounted at PATH (/ is used as
default):
CPU BOGOMIPS
bogomips sum of all CPUs
REGEX/SECOND
regular expressions per second (perl performance test), should be above 300000
HD SIZE
hard disk size
BUFFERED READS
simple HD read test. Modern HDs should reach at least 40 MB/sec
AVERAGE SEEK TIME
tests average seek time. Fast SCSI HDs reach values < 8 milliseconds. Common IDE/SATA disks get
values from 15 to 20 ms.
FSYNCS/SECOND
value should be greater than 200 (you should enable write back cache mode on you RAID controller - needs a battery backed cache (BBWC)).
DNS EXT
average time to resolve an external DNS name
DNS INT
average time to resolve a local DNS name


## 19.3 Shell interface for the Proxmox VE API


The Proxmox VE management tool (pvesh) allows to directly invoke API function, without using the REST/HTTPS
server.

> **Note:**
> Only root is allowed to do that.


### 19.3.1 EXAMPLES


Get the list of nodes in my cluster


```
# pvesh get /nodes
Get a list of available options for the datacenter

# pvesh usage cluster/options -v
Set the HTMl5 NoVNC console as the default console for the datacenter

# pvesh set cluster/options -console html5
```


## See also

- [CLI Reference (Appendix A)](appendix-a-cli/_index.md)

