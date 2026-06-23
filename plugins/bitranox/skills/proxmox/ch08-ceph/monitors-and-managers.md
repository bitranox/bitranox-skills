# Ceph Monitors and Managers

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

This creates an initial configuration at /etc/pve/ceph.conf with a dedicated network for Ceph. This file
is automatically distributed to all Proxmox VE nodes, using pmxcfs. The command also creates a symbolic
link at /etc/ceph/ceph.conf, which points to that file. Thus, you can simply run Ceph commands
without the need to specify a configuration file.


## 8.5 Ceph Monitor


The Ceph Monitor (MON) 2 maintains a master copy of the cluster map. For high availability, you need at
least 3 monitors. One monitor will already be installed if you used the installation wizard. You won’t need
more than 3 monitors, as long as your cluster is small to medium-sized. Only really large clusters will require
more than this.


### 8.5.1 Create Monitors


On each node where you want to place a monitor (three monitors are recommended), create one by using
the Ceph → Monitor tab in the GUI or run:


```
pveceph mon create
```

2 Ceph Monitor https://docs.ceph.com/en/squid/rados/configuration/mon-config-ref/


### 8.5.2 Destroy Monitors


To remove a Ceph Monitor via the GUI, first select a node in the tree view and go to the Ceph → Monitor
panel. Select the MON and click the Destroy button.
To remove a Ceph Monitor via the CLI, first connect to the node on which the MON is running. Then execute
the following command:


```
pveceph mon destroy
```


> **Note:**
> At least three Monitors are needed for quorum.


## 8.6 Ceph Manager


The Manager daemon runs alongside the monitors. It provides an interface to monitor the cluster. Since the
release of Ceph luminous, at least one ceph-mgr 3 daemon is required.


### 8.6.1 Create Manager


Multiple Managers can be installed, but only one Manager is active at any given time.


```
pveceph mgr create
```


> **Note:**
> It is recommended to install the Ceph Manager on the monitor nodes. For high availability install more
> then one manager.


### 8.6.2 Destroy Manager


To remove a Ceph Manager via the GUI, first select a node in the tree view and go to the Ceph → Monitor
panel. Select the Manager and click the Destroy button.
To remove a Ceph Monitor via the CLI, first connect to the node on which the Manager is running. Then
execute the following command:


```
pveceph mgr destroy
```


> **Note:**
> While a manager is not a hard-dependency, it is crucial for a Ceph cluster, as it handles important features
> like PG-autoscaling, device health monitoring, telemetry and more.
> 3 Ceph Manager https://docs.ceph.com/en/squid/mgr/


## 8.7 Ceph OSDs


Ceph Object Storage Daemons store objects for Ceph over the network. It is recommended to use one OSD
per physical disk.


### 8.7.1 Create OSDs


You can create an OSD either via the Proxmox VE web interface or via the CLI using pveceph. For
example:


```
pveceph osd create /dev/sd[X]
```


> **Tip:**
> We recommend a Ceph cluster with at least three nodes and at least 12 OSDs, evenly distributed among
> the nodes.


If the disk was in use before (for example, for ZFS or as an OSD) you first need to zap all traces of that usage.
To remove the partition table, boot sector and any other OSD leftover, you can use the following command:

ceph-volume lvm zap /dev/sd[X] --destroy
