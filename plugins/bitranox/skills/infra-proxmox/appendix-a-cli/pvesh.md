# pvesh - API Shell

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

```
pvesh ls <api_path> [OPTIONS] [FORMAT_OPTIONS]
```

List child objects on <api_path>.

<api_path>: <string>
API path.

- `--noproxy` <boolean>
Disable automatic proxying.

```
pvesh set <api_path> [OPTIONS] [FORMAT_OPTIONS]
```

Call API PUT on <api_path>.

<api_path>: <string>
API path.

- `--noproxy` <boolean>
Disable automatic proxying.

```
pvesh usage <api_path> [OPTIONS]
```

print API usage information for <api_path>.

<api_path>: <string>
API path.

- `--command` <create | delete | get | set>
API command.

- `--returns` <boolean>
Including schema for returned data.

- `--verbose` <boolean>
Verbose output format.


A.9


```
qm - QEMU/KVM Virtual Machine Manager
```


```
qm <COMMAND> [ARGS] [OPTIONS]
```


```
qm agent
```

An alias for qm guest cmd.

```
qm cleanup <vmid> <clean-shutdown> <guest-requested>
```

Cleans up resources like tap devices, vgpus, etc. Called after a vm shuts down, crashes, etc.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<clean-shutdown>: <boolean>
Indicates if qemu shutdown cleanly.

<guest-requested>: <boolean>
Indicates if the shutdown was requested by the guest or via qmp.

```
qm clone <vmid> <newid> [OPTIONS]
```

Create a copy of virtual machine/template.

<vmid>: <integer> (100 - 999999999)
The (unique) ID of the VM.

<newid>: <integer> (100 - 999999999)
VMID for the clone.

- `--bwlimit` <integer> (0 - N) (default = clone limit from datacenter or
storage config)
Override I/O bandwidth limit (in KiB/s).

- `--description` <string>
Description for the new VM.

- `--format` <qcow2 | raw | vmdk>
Target format for file storage. Only valid for full clone.

- `--full` <boolean>
Create a full copy of all disks. This is always done when you clone a normal VM. For VM templates,
we try to create a linked clone by default.

- `--name` <string>
Set a name for the new VM.
