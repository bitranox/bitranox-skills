# Ceph Maintenance and Troubleshooting

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

1. If the disk failed, get a recommended replacement disk of the same type and size.
2. Destroy the OSD in question.
3. Detach the old disk from the server and attach the new one.
4. Create the OSD again.
5. After automatic rebalancing, the cluster status should switch back to HEALTH_OK. Any still listed
crashes can be acknowledged by running the following command:

ceph crash archive-all


### 8.13.2 Trim/Discard


It is good practice to run fstrim (discard) regularly on VMs and containers. This releases data blocks that the
filesystem isn’t using anymore. It reduces data usage and resource load. Most modern operating systems
issue such discard commands to their disks regularly. You only need to ensure that the Virtual Machines
enable the disk discard option.


### 8.13.3 Scrub & Deep Scrub


Ceph ensures data integrity by scrubbing placement groups. Ceph checks every object in a PG for its health.
There are two forms of Scrubbing, daily cheap metadata checks and weekly deep data checks. The weekly
deep scrub reads the objects and uses checksums to ensure data integrity. If a running scrub interferes with
business (performance) needs, you can adjust the time when scrubs 15 are executed.


### 8.13.4 Shutdown Proxmox VE + Ceph HCI Cluster


To shut down the whole Proxmox VE + Ceph cluster, first stop all Ceph clients. These will mainly be VMs
and containers. If you have additional clients that might access a Ceph FS or an installed RADOS GW, stop
these as well. Highly available guests will switch their state to stopped when powered down via the Proxmox
VE tooling.
Once all clients, VMs and containers are off or not accessing the Ceph cluster anymore, verify that the Ceph
cluster is in a healthy state. Either via the Web UI or the CLI:

ceph -s
In order to not cause any recovery during the shut down and later power on phases, enable the noout OSD
flag. Either in the Ceph → OSD panel behind the Manage Global Flags button or the CLI:

ceph osd set noout
Start powering down your nodes without a monitor (MON). After these nodes are down, continue by shutting
down nodes with monitors on them.
When powering on the cluster, start the nodes with monitors (MONs) first. Once all nodes are up and
running, confirm that all Ceph services are up and running. In the end, the only warning you should see for
Ceph is that the noout flag is still set. You can disable it via the web UI or via the CLI:
15 Ceph scrubbing https://docs.ceph.com/en/squid/rados/configuration/osd-config-ref/#scrubbing


ceph osd unset noout
You can now start up the guests. Highly available guests will change their state to started when they power
on.


## 8.14 Ceph Monitoring and Troubleshooting


It is important to continuously monitor the health of a Ceph deployment from the beginning, either by using
the Ceph tools or by accessing the status through the Proxmox VE API.
The following Ceph commands can be used to see if the cluster is healthy (HEALTH_OK ), if there are
warnings (HEALTH_WARN), or even errors (HEALTH_ERR). If the cluster is in an unhealthy state, the
status commands below will also give you an overview of the current events and actions to take. To stop
their execution, press CTRL-C.
Continuously watch the cluster status:

watch ceph --status
Print the cluster status once (not being updated) and continuously append lines of status events:

ceph --watch


### 8.14.1 Troubleshooting


This section includes frequently used troubleshooting information. More information can be found on the
official Ceph website under Troubleshooting 16 .

R ELEVANT L OGS ON A FFECTED N ODE
- Disk Health Monitoring
- System → System Log or via the CLI, for example of the last 2 days:
journalctl --since "2 days ago"

- IPMI and RAID controller logs
Ceph service crashes can be listed and viewed in detail by running the following commands:

ceph crash ls
ceph crash info <crash_id>
Crashes marked as new can be acknowledged by running:

ceph crash archive-all
16 Ceph troubleshooting https://docs.ceph.com/en/squid/rados/troubleshooting/


To get a more detailed view, every Ceph service has a log file under /var/log/ceph/. If more detail is
required, the log level can be adjusted 17 .

C OMMON C AUSES OF C EPH P ROBLEMS
- Network problems like congestion, a faulty switch, a shut down interface or a blocking firewall. Check
whether all Proxmox VE nodes are reliably reachable on the corosync cluster network and on the Ceph
public and cluster network.

- Disk or connection parts which are:
– defective
– not firmly mounted
– lacking I/O performance under higher load (e.g. when using HDDs, consumer hardware or inadvisable
RAID controllers)

- Not fulfilling the recommendations for a healthy Ceph cluster.
C OMMON C EPH P ROBLEMS

OSDs down/crashed
A faulty OSD will be reported as down and mostly (auto) out 10 minutes later. Depending on
the cause, it can also automatically become up and in again. To try a manual activation via web
interface, go to Any node → Ceph → OSD, select the OSD and click on Start, In and Reload.
When using the shell, run following command on the affected node:

ceph-volume lvm activate --all
To activate a failed OSD, it may be necessary to safely reboot the respective node or, as a last
resort, to recreate or replace the OSD.

17 Ceph log and debugging https://docs.ceph.com/en/squid/rados/troubleshooting/log-and-debug/
