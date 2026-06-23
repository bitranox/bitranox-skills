# pveperf

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

A.5


```
pveperf - Proxmox VE Benchmark Script
```


```
pveperf [PATH]
```


A.6


```
pveceph - Manage CEPH Services on Proxmox VE Nodes
```


```
pveceph <COMMAND> [ARGS] [OPTIONS]
```


```
pveceph createmgr
```

An alias for pveceph mgr create.

```
pveceph createmon
```

An alias for pveceph mon create.

```
pveceph createosd
```

An alias for pveceph osd create.

```
pveceph createpool
```

An alias for pveceph pool create.

```
pveceph destroymgr
```

An alias for pveceph mgr destroy.

```
pveceph destroymon
```

An alias for pveceph mon destroy.

```
pveceph destroyosd
```

An alias for pveceph osd destroy.

```
pveceph destroypool
```

An alias for pveceph pool destroy.

```
pveceph fs create [OPTIONS]
```

Create a Ceph filesystem

- `--add-storage` <boolean> (default = 0)
Configure the created CephFS as storage for this cluster.

- `--name` (?ˆ:ˆ[ˆ:/\s]+$) (default = cephfs)
The ceph filesystem name.

- `--pg_num` <integer> (8 - 32768) (default = 128)
Number of placement groups for the backing data pool. The metadata pool will use a quarter of this.

```
pveceph fs destroy <name> [OPTIONS]
```

Destroy a Ceph filesystem


<name>: <string>
The ceph filesystem name.

- `--remove-pools` <boolean> (default = 0)
Remove data and metadata pools configured for this fs.

- `--remove-storages` <boolean> (default = 0)
Remove all pveceph-managed storages configured for this fs.

```
pveceph help [OPTIONS]
```

Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

```
pveceph init [OPTIONS]
```

Create initial ceph default configuration and setup symlinks.

- `--cluster-network` <string>
Declare a separate cluster network, OSDs will routeheartbeat, object replication and recovery traffic
over it

> **Note:**
> Requires option(s): network


- `--disable_cephx` <boolean> (default = 0)
Disable cephx authentication.


> **Warning:**
> cephx is a security feature protecting against man-in-the-middle attacks. Only consider disabling cephx if your network is private!


- `--min_size` <integer> (1 - 7) (default = 2)
Minimum number of available replicas per object to allow I/O

- `--network` <string>
Use specific network for all ceph related traffic
