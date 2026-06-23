# Ceph Pools and Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

To persistently change configuration values use the following commands 6 :

ceph config dump
ceph config get <who> <name>
ceph config set <who> <name>
<value>
ceph config rm <who> <name>

Show all configuration option(s)
Show configuration option(s) for an entity
Set a configuration option for one or more entities
Clear a configuration option for one or more
entities

Example for increasing the osd_memory_target for all OSD daemons

ceph config set osd osd_memory_target 8G

> **Note:**
> If an option exists in a local configuration file, the configuration in the MON DB will be ignored because it
> has a lower precedence.


## 8.9 Ceph Pools


A pool is a logical group for storing objects. It holds a collection of objects, known as Placement Groups (PG,
pg_num).
6 Ceph MON DB commands https://docs.ceph.com/en/latest/rados/configuration/ceph-conf/#commands


### 8.9.1 Create and Edit Pools


You can create and edit pools from the command line or the web interface of any Proxmox VE host under
Ceph → Pools.
When no options are given, we set a default of 128 PGs, a size of 3 replicas and a min_size of 2 replicas,
to ensure no data loss occurs if any OSD fails.


> **Warning:**
> Do not set a min_size of 1. A replicated pool with min_size of 1 allows I/O on an object when it
> has only 1 replica, which could lead to data loss, incomplete PGs or unfound objects.


It is advised that you either enable the PG-Autoscaler or calculate the PG number based on your setup.
You can find the formula and the PG calculator 7 online. From Ceph Nautilus onward, you can change the
number of PGs 8 after the setup.
The PG autoscaler 9 can automatically scale the PG count for a pool in the background. Setting the Target
Size or Target Ratio advanced parameters helps the PG-Autoscaler to make better decisions.
Example for creating a pool over the CLI


```
pveceph pool create <pool-name> --add_storages
```


> **Tip:**
> If you would also like to automatically define a storage for your pool, keep the ‘Add as Storage’ checkbox
> checked in the web interface, or use the command-line option --add_storages at pool creation.


Pool Options

The following options are available on pool creation, and partially also when editing a pool.

Name
The name of the pool. This must be unique and can’t be changed afterwards.
7 PG calculator https://web.archive.org/web/20210301111112/http://ceph.com/pgcalc/
8 Placement Groups https://docs.ceph.com/en/squid/rados/operations/placement-groups/
9 Automated Scaling https://docs.ceph.com/en/squid/rados/operations/placement-groups/#automated-scaling


Size
The number of replicas per object. Ceph always tries to have this many copies of an object. Default:
3.
PG Autoscale Mode
The automatic PG scaling mode 9 of the pool. If set to warn, it produces a warning message when a
pool has a non-optimal PG count. Default: warn.
Add as Storage
Configure a VM or container storage using the new pool. Default: true (only visible on creation).

A DVANCED O PTIONS

Min. Size
The minimum number of replicas per object. Ceph will reject I/O on the pool if a PG has less than this
many replicas. Default: 2.
Crush Rule
The rule to use for mapping object placement in the cluster. These rules define how data is placed
within the cluster. See Ceph CRUSH & device classes for information on device-based rules.
# of PGs
The number of placement groups 8 that the pool should have at the beginning. Default: 128.
Target Ratio
The ratio of data that is expected in the pool. The PG autoscaler uses the ratio relative to other ratio
sets. It takes precedence over the target size if both are set.
Target Size
The estimated amount of data expected in the pool. The PG autoscaler uses this size to estimate the
optimal PG count.
Min. # of PGs
The minimum number of placement groups. This setting is used to fine-tune the lower bound of the
PG count for that pool. The PG autoscaler will not merge PGs below this threshold.
Further information on Ceph pool handling can be found in the Ceph pool operation 10 manual.


### 8.9.2 Erasure Coded Pools


Erasure coding (EC) is a form of ‘forward error correction’ codes that allows to recover from a certain amount
of data loss. Erasure coded pools can offer more usable space compared to replicated pools, but they do
that for the price of performance.
10 Ceph pool operation https://docs.ceph.com/en/squid/rados/operations/pools/


For comparison: in classic, replicated pools, multiple replicas of the data are stored (size) while in erasure
coded pool, data is split into k data chunks with additional m coding (checking) chunks. Those coding chunks
can be used to recreate data should data chunks be missing.
The number of coding chunks, m, defines how many OSDs can be lost without losing any data. The total
amount of objects stored is k + m.

Creating EC Pools
Erasure coded (EC) pools can be created with the pveceph CLI tooling. Planning an EC pool needs to
account for the fact, that they work differently than replicated pools.
The default min_size of an EC pool depends on the m parameter. If m = 1, the min_size of the
EC pool will be k. The min_size will be k + 1 if m > 1. The Ceph documentation recommends a
conservative min_size of k + 2 11 .
If there are less than min_size OSDs available, any IO to the pool will be blocked until there are enough
OSDs available again.

> **Note:**
> When planning an erasure coded pool, keep an eye on the min_size as it defines how many OSDs
> need to be available. Otherwise, IO will be blocked.


For example, an EC pool with k = 2 and m = 1 will have size = 3, min_size = 2 and will stay
operational if one OSD fails. If the pool is configured with k = 2, m = 2, it will have a size = 4 and
min_size = 3 and stay operational if one OSD is lost.
To create a new EC pool, run the following command:


```
pveceph pool create <pool-name> --erasure-coding k=2,m=1
```

Optional parameters are failure-domain and device-class. If you need to change any EC profile
settings used by the pool, you will have to create a new pool with a new profile.
This will create a new EC pool plus the needed replicated pool to store the RBD omap and other metadata.
In the end, there will be a <pool name>-data and <pool name>-metadata pool. The default
behavior is to create a matching storage configuration as well. If that behavior is not wanted, you can disable
it by providing the --add_storages 0 parameter. When configuring the storage configuration manually,
keep in mind that the data-pool parameter needs to be set. Only then will the EC pool be used to store
the data objects. For example:

> **Note:**
> The optional parameters --size, --min_size and --crush_rule will be used for the replicated
> metadata pool, but not for the erasure coded data pool. If you need to change the min_size on the data
> pool, you can do it later. The size and crush_rule parameters cannot be changed on erasure coded
> pools.
> 11 Ceph Erasure Coded Pool Recovery https://docs.ceph.com/en/squid/rados/operations/erasure-code/#erasure-coded-pool-


recovery


If there is a need to further customize the EC profile, you can do so by creating it with the Ceph tools directly
12 , and specify the profile to use with the profile parameter.
For example:


```
pveceph pool create <pool-name> --erasure-coding profile=<profile-name>
```


Adding EC Pools as Storage
You can add an already existing EC pool as storage to Proxmox VE. It works the same way as adding an
RBD pool but requires the extra data-pool option.


```
pvesm add rbd <storage-name> --pool <replicated-pool> --data-pool <ec-pool>
```


> **Tip:**
> Do not forget to add the keyring and monhost option for any external Ceph clusters, not managed by
> the local Proxmox VE cluster.


### 8.9.3 Destroy Pools


To destroy a pool via the GUI, select a node in the tree view and go to the Ceph → Pools panel. Select the
pool to destroy and click the Destroy button. To confirm the destruction of the pool, you need to enter the
pool name.
Run the following command to destroy a pool. Specify the -remove_storages to also remove the associated
storage.


```
pveceph pool destroy <name>
```


> **Note:**
> Pool deletion runs in the background and can take some time. You will notice the data usage in the cluster
> decreasing throughout this process.


### 8.9.4 PG Autoscaler


The PG autoscaler allows the cluster to consider the amount of (expected) data stored in each pool and to
choose the appropriate pg_num values automatically. It is available since Ceph Nautilus.
You may need to activate the PG autoscaler module before adjustments can take effect.

ceph mgr module enable pg_autoscaler
The autoscaler is configured on a per pool basis and has the following modes:

12 Ceph Erasure Code Profile https://docs.ceph.com/en/squid/rados/operations/erasure-code/#erasure-code-profiles

warn
on
off


A health warning is issued if the suggested pg_num value differs too much from the
current value.
The pg_num is adjusted automatically with no need for any manual interaction.
No automatic pg_num adjustments are made, and no warning will be issued if the
PG count is not optimal.

The scaling factor can be adjusted to facilitate future data storage with the target_size, target_size_rati
and the pg_num_min options.


> **Warning:**
> By default, the autoscaler considers tuning the PG count of a pool if it is off by a factor of 3. This
> will lead to a considerable shift in data placement and might introduce a high load on the cluster.


You can find a more in-depth introduction to the PG autoscaler on Ceph’s Blog - New in Nautilus: PG merging
and autotuning.


## 8.10 Ceph CRUSH & Device Classes


The 13 (Controlled Replication Under Scalable Hashing) algorithm is at the foundation of Ceph.
13 https://ceph.com/assets/pdfs/weil-crush-sc06.pdf
