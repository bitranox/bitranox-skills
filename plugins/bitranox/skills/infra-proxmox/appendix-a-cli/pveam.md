# pveam - Appliance Manager

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

A.12


```
pveam - Proxmox VE Appliance Manager
```


```
pveam <COMMAND> [ARGS] [OPTIONS]
```


```
pveam available [OPTIONS]
```

List available templates.

- `--section` <mail | system | turnkeylinux>
Restrict list to specified section.

```
pveam download <storage> <template>
```

Download appliance templates.

<storage>: <storage ID>
The storage where the template will be stored

<template>: <string>
The template which will downloaded

```
pveam help [OPTIONS]
```

Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

```
pveam list <storage>
```

Get list of all templates on storage

<storage>: <storage ID>
Only list templates on specified storage

```
pveam remove <template_path>
```

Remove a template.

<template_path>: <string>
The template to remove.

```
pveam update
```

Update Container Template Database.


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
