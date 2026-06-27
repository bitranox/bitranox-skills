# qmrestore

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--timeout` <integer> (1 - N)
Timeout in seconds. Default is to wait forever.

A.10


```
qmrestore - Restore QemuServer vzdump Backups
```


```
qmrestore help
```


```
qmrestore <archive> <vmid> [OPTIONS]
```

Restore QemuServer vzdump backups.

<archive>: <string>
The backup file. You can pass - to read from standard input.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

- `--bwlimit` <number> (0 - N)
Override I/O bandwidth limit (in KiB/s).

- `--force` <boolean>
Allow to overwrite existing VM.

- `--ha-managed` <boolean> (default = 0)
Add the VM as a HA resource after it was restored.

- `--live-restore` <boolean>
Start the VM immediately from the backup and restore in background. PBS only.

- `--pool` <string>
Add the VM to the specified pool.

- `--start` <boolean> (default = 0)
Start VM after it was restored successfully.

- `--storage` <storage ID>
Default storage.

- `--unique` <boolean>
Assign a unique random ethernet address.


A.11


```
pct - Proxmox Container Toolkit
```


```
pct <COMMAND> [ARGS] [OPTIONS]
```


```
pct clone <vmid> <newid> [OPTIONS]
```

Create a container clone/copy

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<newid>: <integer> (100 - 999999999)
VMID for the clone.

- `--bwlimit` <number> (0 - N) (default = clone limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--description` <string>
Description for the new CT.

- `--full` <boolean>
Create a full copy of all disks. This is always done when you clone a normal CT. For CT templates, we
try to create a linked clone by default.

- `--hostname` <string>
Set a hostname for the new CT.

- `--pool` <string>
Add the new CT to the specified pool.

- `--snapname` <string>
The name of the snapshot.

- `--storage` <storage ID>
Target storage for full clone.

- `--target` <string>
Target node. Only allowed if the original VM is on shared storage.

```
pct config <vmid> [OPTIONS]
```

Get container configuration.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.
