# Command-line Interface

*[Main Index](../SKILL.md)*

## Contents

| Section                                | File                                                           |
|----------------------------------------|----------------------------------------------------------------|
| A.1-A.2 General and Format Options     | [general-and-format-options.md](general-and-format-options.md) |
| A.3 pvesm - Proxmox VE Storage Manager | [pvesm.md](pvesm.md)                                           |
| A.4 pvesubscription                    | [pvesubscription.md](pvesubscription.md)                       |
| A.5 pveperf                            | [pveperf.md](pveperf.md)                                       |
| A.6 pveceph - Manage Ceph Services     | [pveceph.md](pveceph.md)                                       |
| A.7 pvenode - Node Management          | [pvenode.md](pvenode.md)                                       |
| A.8 pvesh - API Shell                  | [pvesh.md](pvesh.md)                                           |
| A.9 qm - QEMU/KVM VM Manager           | [qm.md](qm.md)                                                 |
| A.9 qm (create cont. - help)           | [qm-create-help.md](qm-create-help.md)                         |
| A.9 qm (import - listsnapshot)         | [qm-import-listsnapshot.md](qm-import-listsnapshot.md)         |
| A.9 qm (listsnapshot - set)            | [qm-listsnapshot-set.md](qm-listsnapshot-set.md)               |
| A.9 qm (set cont. - wait)              | [qm-set-wait.md](qm-set-wait.md)                               |
| A.10 qmrestore                         | [qmrestore.md](qmrestore.md)                                   |
| A.11 pct - Proxmox Container Toolkit   | [pct.md](pct.md)                                               |
| A.11 pct (list - resize)               | [pct-list-resize.md](pct-list-resize.md)                       |
| A.11 pct (restore - unmount)           | [pct-restore-unmount.md](pct-restore-unmount.md)               |
| A.12 pveam - Appliance Manager         | [pveam.md](pveam.md)                                           |
| A.13 pvecm - Cluster Manager           | [pvecm.md](pvecm.md)                                           |
| A.14 pvesr - Storage Replication       | [pvesr.md](pvesr.md)                                           |
| A.15 pveum - User Manager              | [pveum.md](pveum.md)                                           |
| A.16 vzdump - Backup Utility           | [vzdump.md](vzdump.md)                                         |
| A.17 ha-manager - HA Manager           | [ha-manager.md](ha-manager.md)                                 |


## See also

- [Useful Command-line Tools](../ch19-cli-tools.md)

## Overview


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
