# pvecm - Cluster Manager

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

A.13


```
pvecm - Proxmox VE Cluster Manager
```


```
pvecm <COMMAND> [ARGS] [OPTIONS]
```


```
pvecm add <hostname> [OPTIONS]
```

Adds the current node to an existing cluster.

<hostname>: <string>
Hostname (or IP) of an existing cluster member.

- `--fingerprint` ([A-Fa-f0-9]{2}:){31}[A-Fa-f0-9]{2}
Certificate SHA 256 fingerprint.

- `--force` <boolean>
Do not throw error if node already exists.

--link[n] [address=]<IP> [,priority=<integer>]
Address and priority information of a single corosync link. (up to 8 links supported; link0..link7)

- `--nodeid` <integer> (1 - N)
Node id for this node.

- `--use_ssh` <boolean>
Always use SSH to join, even if peer may do it over API.

- `--votes` <integer> (0 - N)
Number of votes for this node

```
pvecm addnode <node> [OPTIONS]
```

Adds a node to the cluster configuration. This call is for internal use.

<node>: <string>
The cluster node name.

- `--apiversion` <integer>
The JOIN_API_VERSION of the new node.

- `--force` <boolean>
Do not throw error if node already exists.

--link[n] [address=]<IP> [,priority=<integer>]
Address and priority information of a single corosync link. (up to 8 links supported; link0..link7)

- `--new_node_ip` <string>
IP Address of node to add. Used as fallback if no links are given.


- `--nodeid` <integer> (1 - N)
Node id for this node.

- `--votes` <integer> (0 - N)
Number of votes for this node

```
pvecm apiver
```

Return the version of the cluster join API available on this node.

```
pvecm create <clustername> [OPTIONS]
```

Generate new cluster configuration. If no links given, default to local IP address as link0.

<clustername>: <string>
The name of the cluster.

--link[n] [address=]<IP> [,priority=<integer>]
Address and priority information of a single corosync link. (up to 8 links supported; link0..link7)

- `--nodeid` <integer> (1 - N)
Node id for this node.

- `--votes` <integer> (1 - N)
Number of votes for this node.

```
pvecm delnode <node>
```

Removes a node from the cluster configuration.

<node>: <string>
The cluster node name.

```
pvecm expected <expected>
```

Tells corosync a new value of expected votes.

<expected>: <integer> (1 - N)
Expected votes

```
pvecm help [OPTIONS]
```

Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.


```
pvecm keygen <filename>
```

Generate new cryptographic key for corosync.

<filename>: <string>
Output file name

```
pvecm mtunnel [<extra-args>] [OPTIONS]
```

Used by VM/CT migration - do not use manually.

<extra-args>: <array>
Extra arguments as array

- `--get_migration_ip` <boolean> (default = 0)
return the migration IP, if configured

- `--migration_network` <string>
the migration network used to detect the local migration IP

- `--run-command` <boolean>
Run a command with a tcp socket as standard input. The IP address and port are printed via this
command’s stdandard output first, each on a separate line.

```
pvecm nodes
```

Displays the local view of the cluster nodes.

```
pvecm qdevice remove
```

Remove a configured QDevice

```
pvecm qdevice setup <address> [OPTIONS]
```

Setup the use of a QDevice

<address>: <string>
Specifies the network address of an external corosync QDevice

- `--force` <boolean>
Do not throw error on possible dangerous operations.

- `--network` <string>
The network which should be used to connect to the external qdevice

```
pvecm status
```

Displays the local view of the cluster status.

```
pvecm updatecerts [OPTIONS]
```

Update node certificates (and generate all needed files/directories).


- `--force` <boolean>
Force generation of new SSL certificate.

- `--silent` <boolean>
Ignore errors (i.e. when cluster has no quorum).

- `--unmerge-known-hosts` <boolean> (default = 0)
Unmerge legacy SSH known hosts.

A.14


```
pvesr - Proxmox VE Storage Replication
```


```
pvesr <COMMAND> [ARGS] [OPTIONS]
```


```
pvesr create-local-job <id> <target> [OPTIONS]
```

Create a new replication job

<id>: [1-9][0-9]{2,8}-\d{1,9}
Replication Job ID. The ID is composed of a Guest ID and a job number, separated by a hyphen, i.e.
<GUEST>-<JOBNUM>.

<target>: <string>
Target node.

- `--comment` <string>
Description.

- `--disable` <boolean>
Flag to disable/deactivate the entry.

- `--rate` <number> (1 - N)
Rate limit in mbps (megabytes per second) as floating point number.

- `--remove_job` <full | local>
Mark the replication job for removal. The job will remove all local replication snapshots. When set
to full, it also tries to remove replicated volumes on the target. The job then removes itself from the
configuration file.

- `--schedule` <string> (default = */15)
Storage replication schedule. The format is a subset of systemd calendar events.

- `--source` <string>
For internal use, to detect if the guest was stolen.

```
pvesr delete <id> [OPTIONS]
```

Mark replication job for removal.


<id>: [1-9][0-9]{2,8}-\d{1,9}
Replication Job ID. The ID is composed of a Guest ID and a job number, separated by a hyphen, i.e.
<GUEST>-<JOBNUM>.

- `--force` <boolean> (default = 0)
Will remove the jobconfig entry, but will not cleanup.

- `--keep` <boolean> (default = 0)
Keep replicated data at target (do not remove).

```
pvesr disable <id>
```

Disable a replication job.

<id>: [1-9][0-9]{2,8}-\d{1,9}
Replication Job ID. The ID is composed of a Guest ID and a job number, separated by a hyphen, i.e.
<GUEST>-<JOBNUM>.

```
pvesr enable <id>
```

Enable a replication job.

<id>: [1-9][0-9]{2,8}-\d{1,9}
Replication Job ID. The ID is composed of a Guest ID and a job number, separated by a hyphen, i.e.
<GUEST>-<JOBNUM>.

```
pvesr finalize-local-job <id> [<extra-args>] [OPTIONS]
```

Finalize a replication job. This removes all replications snapshots with timestamps different than <last_sync>.

<id>: [1-9][0-9]{2,8}-\d{1,9}
Replication Job ID. The ID is composed of a Guest ID and a job number, separated by a hyphen, i.e.
<GUEST>-<JOBNUM>.

<extra-args>: <array>
The list of volume IDs to consider.

- `--last_sync` <integer> (0 - N)
Time (UNIX epoch) of last successful sync. If not specified, all replication snapshots gets removed.

```
pvesr help [OPTIONS]
```

Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

## See also

- [Cluster Manager](../ch05-cluster-manager/_index.md)

