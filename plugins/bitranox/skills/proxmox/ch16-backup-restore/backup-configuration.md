# Backup Configuration and vzdump

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 16.10 Configuration


Global configuration is stored in /etc/vzdump.conf. The file uses a simple colon separated key/value
format. Each line has the following format:

OPTION: value
Blank lines in the file are ignored, and lines starting with a # character are treated as comments and are also
ignored. Values from this file are used as default, and can be overwritten on the command line.
We currently support the following options:

bwlimit: <integer> (0 - N) (default = 0)
Limit I/O bandwidth (in KiB/s).

compress: <0 | 1 | gzip | lzo | zstd> (default = 0)
Compress dump file.

dumpdir: <string>
Store resulting files to specified directory.

exclude-path: <array>
Exclude certain files/directories (shell globs). Paths starting with / are anchored to the container’s
root, other paths match relative to each subdirectory.

fleecing: [[enabled=]<1|0>] [,storage=<storage ID>]
Options for backup fleecing (VM only).

enabled=<boolean> (default = 0)
Enable backup fleecing. Cache backup data from blocks where new guest writes happen on
specified storage instead of copying them directly to the backup target. This can help guest IO
performance and even prevent hangs, at the cost of requiring more storage space.

storage=<storage ID>
Use this storage to storage fleecing images. For efficient space usage, it’s best to use a local
storage that supports discard and either thin provisioning or sparse files.

ionice: <integer> (0 - 8) (default = 7)
Set IO priority when using the BFQ scheduler. For snapshot and suspend mode backups of VMs, this
only affects the compressor. A value of 8 means the idle priority is used, otherwise the best-effort
priority is used with the specified value.

lockwait: <integer> (0 - N) (default = 180)
Maximal time to wait for the global lock (minutes).

mailnotification: <always | failure> (default = always)
Deprecated: use notification targets/matchers instead. Specify when to send a notification mail


mailto: <string>
Deprecated: Use notification targets/matchers instead. Comma-separated list of email addresses or
users that should receive email notifications.

maxfiles: <integer> (1 - N)
Deprecated: use prune-backups instead. Maximal number of backup files per guest system.

mode: <snapshot | stop | suspend> (default = snapshot)
Backup mode.

notes-template: <string>
Template string for generating notes for the backup(s). It can contain variables which will be replaced
by their values. Currently supported are {\{\cluster}}, {\{\guestname}}, {\{\node}}, and {\{\vmid}}, but
more might be added in the future. Needs to be a single line, newline and backslash need to be
escaped as \n and \\ respectively.

> **Note:**
> Requires option(s): storage


notification-mode: <auto | legacy-sendmail | notification-system>
(default = auto)
Determine which notification system to use. If set to legacy-sendmail, vzdump will consider the mailto/mailnotification parameters and send emails to the specified address(es) via the sendmail command.
If set to notification-system, a notification will be sent via PVE’s notification system, and the mailto and
mailnotification will be ignored. If set to auto (default setting), an email will be sent if mailto is set, and
the notification system will be used if not.

pbs-change-detection-mode: <data | legacy | metadata>
PBS mode used to detect file changes and switch encoding format for container backups.

performance: [max-workers=<integer>] [,pbs-entries-max=<integer>]
Other performance-related settings.

max-workers=<integer> (1 - 256) (default = 16)
Applies to VMs. Allow up to this many IO workers at the same time.

pbs-entries-max=<integer> (1 - N) (default = 1048576)
Applies to container backups sent to PBS. Limits the number of entries allowed in memory at a
given time to avoid unintended OOM situations. Increase it to enable backups of containers with
a large amount of files.

pigz: <integer> (default = 0)
Use pigz instead of gzip when N>0. N=1 uses half of cores, N>1 uses N as thread count.

pool: <string>
Backup all known guest systems included in the specified pool.


protected: <boolean>
If true, mark backup(s) as protected.

> **Note:**
> Requires option(s): storage


prune-backups: [keep-all=<1|0>] [,keep-daily=<N>] [,keep-hourly=<N>]
[,keep-last=<N>] [,keep-monthly=<N>] [,keep-weekly=<N>]
[,keep-yearly=<N>] (default = keep-all=1)
Use these retention options instead of those from the storage configuration.

keep-all=<boolean>
Keep all backups. Conflicts with the other options when true.

keep-daily=<N>
Keep backups for the last <N> different days. If there is morethan one backup for a single day,
only the latest one is kept.

keep-hourly=<N>
Keep backups for the last <N> different hours. If there is morethan one backup for a single hour,
only the latest one is kept.

keep-last=<N>
Keep the last <N> backups.

keep-monthly=<N>
Keep backups for the last <N> different months. If there is morethan one backup for a single
month, only the latest one is kept.

keep-weekly=<N>
Keep backups for the last <N> different weeks. If there is morethan one backup for a single week,
only the latest one is kept.

keep-yearly=<N>
Keep backups for the last <N> different years. If there is morethan one backup for a single year,
only the latest one is kept.

remove: <boolean> (default = 1)
Prune older backups according to prune-backups.

script: <string>
Use specified hook script.

stdexcludes: <boolean> (default = 1)
Exclude temporary files and logs.

stopwait: <integer> (0 - N) (default = 10)
Maximal time to wait until a guest system is stopped (minutes).


storage: <storage ID>
Store resulting file to this storage.

tmpdir: <string>
Store temporary files to specified directory.

zstd: <integer> (default = 1)
Zstd threads. N=0 uses half of the available cores, if N is set to a value bigger than 0, N is used as
thread count.
Example vzdump.conf Configuration

tmpdir: /mnt/fast_local_disk
storage: my_backup_storage
mode: snapshot
bwlimit: 10000


## 16.11 Hook Scripts


You can specify a hook script with option --script. This script is called at various phases of the
backup process, with parameters accordingly set. You can find an example in the documentation directory
(vzdump-hook-script.pl).


## 16.12 File Exclusions


> **Note:**
> this option is only available for container backups.


```
vzdump skips the following files by default (disable with the option --stdexcludes 0)
```

/tmp/?*
/var/tmp/?*
/var/run/?*pid
You can also manually specify (additional) exclude paths, for example:


```
# vzdump 777 --exclude-path /tmp/ --exclude-path '/var/foo*'
excludes the directory /tmp/ and any file or directory named /var/foo, /var/foobar, and so on.
Warning
For backups to Proxmox Backup Server (PBS) and suspend mode backups, patterns with a trailing slash will match directories, but not files. On the other hand, for non-PBS snapshot mode
and stop mode backups, patterns with a trailing slash currently do not match at all, because the
tar command does not support that.
```


Paths that do not start with a / are not anchored to the container’s root, but will match relative to any
subdirectory. For example:


```
# vzdump 777 --exclude-path bar
excludes any file or directory named /bar, /var/bar, /var/foo/bar, and so on, but not /bar2.
Configuration files are also stored inside the backup archive (in ./etc/vzdump/) and will be correctly
restored.
```


## 16.13 Examples


Simply dump guest 777 - no snapshot, just archive the guest private area and configuration files to the default
dump directory (usually /var/lib/vz/dump/).


```
# vzdump 777
Use rsync and suspend/resume to create a snapshot (minimal downtime).

# vzdump 777 --mode suspend
Backup all guest systems and send notification mails to root and admin. Due to mailto being set and
notification-mode being set to auto by default, the notification mails are sent via the system’s
sendmail command instead of the notification system.

# vzdump --all --mode suspend --mailto root --mailto admin
Use snapshot mode (no downtime) and non-default dump directory.

# vzdump 777 --dumpdir /mnt/backup --mode snapshot
Backup more than one guest (selectively)

# vzdump 101 102 103 --mailto root
Backup all guests excluding 101 and 102

# vzdump --mode suspend --exclude 101,102
Restore a container to a new CT 600

# pct restore 600 /mnt/backup/vzdump-lxc-777.tar
Restore a QemuServer VM to VM 601

# qmrestore /mnt/backup/vzdump-qemu-888.vma 601
Clone an existing container 101 to a new container 300 with a 4GB root file system, using pipes

# vzdump 101 --stdout | pct restore --rootfs 4 300 -
```


## See also

## See also

- [Backup and Restore Overview](_index.md)
- [Backup Retention and Restore](backup-retention-restore.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
- [Containers](../ch11-containers/_index.md)
- [vzdump CLI Reference](../appendix-a-cli/vzdump.md)
