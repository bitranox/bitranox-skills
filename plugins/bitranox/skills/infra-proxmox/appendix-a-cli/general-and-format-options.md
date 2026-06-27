# General and Format Options

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## A.1 General


Regarding the historically non-uniform casing style for options, see the related section for configuration files.


## A.2 Output format options [FORMAT_OPTIONS]


It is possible to specify the output format using the --output-format parameter. The default format
text uses ASCII-art to draw nice borders around tables. It additionally transforms some values into humanreadable text, for example:

- Unix epoch is displayed as ISO 8601 date string.
- Durations are displayed as week/day/hour/minute/second count, i.e 1d 5h.
- Byte sizes value include units (B, KiB, MiB, GiB, TiB, PiB).
- Fractions are display as percentage, i.e. 1.0 is displayed as 100%.
You can also completely suppress output using option --quiet.

- `--human-readable` <boolean> (default = 1)
Call output rendering functions to produce human readable text.

- `--noborder` <boolean> (default = 0)
Do not draw borders (for text format).

- `--noheader` <boolean> (default = 0)
Do not show column headers (for text format).

- `--output-format` <json | json-pretty | text | yaml> (default = text)
Output format.

- `--quiet` <boolean>
Suppress printing results.


A.3


```
pvesm - Proxmox VE Storage Manager
```


```
pvesm <COMMAND> [ARGS] [OPTIONS]
```


```
pvesm add <type> <storage> [OPTIONS]
```

Create a new storage.

<type>: <btrfs | cephfs | cifs | dir | esxi | iscsi | iscsidirect |
lvm | lvmthin | nfs | pbs | rbd | zfs | zfspool>
Storage type.

<storage>: <storage ID>
The storage identifier.

- `--authsupported` <string>
Authsupported.

- `--base` <string>
Base volume. This volume is automatically activated.

- `--blocksize` <string>
block size

- `--bwlimit` [clone=<LIMIT>] [,default=<LIMIT>] [,migration=<LIMIT>]
[,move=<LIMIT>] [,restore=<LIMIT>]
Set I/O bandwidth limit for various operations (in KiB/s).

- `--comstar_hg` <string>
host group for comstar views

- `--comstar_tg` <string>
target group for comstar views

- `--content` <string>
Allowed content types.

> **Note:**
> the value rootdir is used for Containers, and value images for VMs.


- `--content-dirs` <string>
Overrides for default content type directories.

- `--create-base-path` <boolean> (default = yes)
Create the base directory if it doesn’t exist.
