# Time Synchronization

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.4.10 Disabling MAC Learning on a Bridge


By default, MAC learning is enabled on a bridge to ensure a smooth experience with virtual guests and their
networks.
But in some environments this can be undesired. Since Proxmox VE 7.3 you can disable MAC learning on the
bridge by setting the ‘bridge-disable-mac-learning 1` configuration on a bridge in `/etc/network/interfaces’,
for example:

# ...
auto vmbr0
iface vmbr0 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports ens18
bridge-stp off
bridge-fd 0
bridge-disable-mac-learning 1
Once enabled, Proxmox VE will manually add the configured MAC address from VMs and Containers to the
bridges forwarding database to ensure that guest can still use the network - but only when they are using
their actual MAC address.


## 3.5 Time Synchronization


The Proxmox VE cluster stack itself relies heavily on the fact that all the nodes have precisely synchronized
time. Some other components, like Ceph, also won’t work properly if the local time on all nodes is not in
sync.
Time synchronization between nodes can be achieved using the “Network Time Protocol” (NTP). As of Proxmox VE 7, chrony is used as the default NTP daemon, while Proxmox VE 6 uses systemd-timesyncd.
Both come preconfigured to use a set of public servers.


> **Important:**
> If you upgrade your system to Proxmox VE 7, it is recommended that you manually install either
> chrony, ntp or openntpd.


### 3.5.1 Using Custom NTP Servers


In some cases, it might be desired to use non-default NTP servers. For example, if your Proxmox VE nodes
do not have access to the public internet due to restrictive firewall rules, you need to set up local NTP servers
and tell the NTP daemon to use them.

For systems using chrony:
Specify which servers chrony should use in /etc/chrony/chrony.conf:


server ntp1.example.com iburst
server ntp2.example.com iburst
server ntp3.example.com iburst
Restart chrony:


```
# systemctl restart chronyd
Check the journal to confirm that the newly configured NTP servers are being used:

# journalctl --since -1h -u chrony
...
Aug 26 13:00:09 node1 systemd[1]: Started chrony, an NTP client/server.
Aug 26 13:00:15 node1 chronyd[4873]: Selected source 10.0.0.1 (ntp1.example ←.com)
Aug 26 13:00:15 node1 chronyd[4873]: System clock TAI offset set to 37 ←seconds
...
```


For systems using systemd-timesyncd:
Specify which servers systemd-timesyncd should use in /etc/systemd/timesyncd.conf:

[Time]
NTP=ntp1.example.com ntp2.example.com ntp3.example.com ntp4.example.com
Then, restart the synchronization service (systemctl restart systemd-timesyncd), and verify
that your newly configured NTP servers are in use by checking the journal (journalctl --since -1h
-u systemd-timesyncd):

...
Oct 07 14:58:36 node1 systemd[1]: Stopping Network Time Synchronization...
Oct 07 14:58:36 node1 systemd[1]: Starting Network Time Synchronization...
Oct 07 14:58:36 node1 systemd[1]: Started Network Time Synchronization.
Oct 07 14:58:36 node1 systemd-timesyncd[13514]: Using NTP server ←10.0.0.1:123 (ntp1.example.com).
Oct 07 14:58:36 node1 systemd-timesyncd[13514]: interval/delta/delay/jitter ←/drift 64s/-0.002s/0.020s/0.000s/-31ppm
...


## 3.6 External Metric Server


In Proxmox VE, you can define external metric servers, which will periodically receive various stats about
your hosts, virtual guests and storages.
Currently supported are:

- Graphite (see https://graphiteapp.org )
- InfluxDB (see https://www.influxdata.com/time-series-platform/influxdb/ )
The external metric server definitions are saved in /etc/pve/status.cfg, and can be edited through the web
interface.


### 3.6.1 Graphite server configuration

