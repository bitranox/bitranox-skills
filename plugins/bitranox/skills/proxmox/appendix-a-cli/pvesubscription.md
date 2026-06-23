# pvesubscription

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

- `--storage` <storage ID>
Only list status for specified storage

- `--target` <string>
If target is different to node, we only lists shared storages which content is accessible on this node and
the specified target node.

```
pvesm zfsscan
```

An alias for pvesm scan zfs.

A.4


```
pvesubscription - Proxmox VE Subscription Manager
```


```
pvesubscription <COMMAND> [ARGS] [OPTIONS]
```


```
pvesubscription delete
```

Delete subscription key of this node.

```
pvesubscription get
```

Read subscription info.

```
pvesubscription help [OPTIONS]
```

Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

```
pvesubscription set <key>
```

Set subscription key.

<key>: \s*pve([1248])([cbsp])-[0-9a-f]{10}\s*
Proxmox VE subscription key

```
pvesubscription set-offline-key <data>
```

Internal use only! To set an offline key, use the package proxmox-offline-mirror-helper instead.

<data>: <string>
A signed subscription info blob

```
pvesubscription update [OPTIONS]
```

Update subscription info.

- `--force` <boolean> (default = 0)
Always connect to server, even if local cache is still valid.


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
