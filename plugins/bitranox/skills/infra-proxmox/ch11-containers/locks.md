# Container Locks

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

template: <boolean> (default = 0)
Enable/disable Template.

timezone: <string>
Time zone to use in the container. If option isn't set, then nothing will be done. Can be set to host to
match the host time zone, or an arbitrary time zone option from /usr/share/zoneinfo/zone.tab

tty: <integer> (0 - 6) (default = 2)
Specify the number of tty available to the container

unprivileged: <boolean> (default = 0)
Makes the container run as unprivileged user. For creation, the default is 1. For restore, the default is
the value from the backup. (Should not be modified manually.)

unused[n]: [volume=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

volume=<volume>
The volume that is not used currently.


## 11.12 Locks


Container migrations, snapshots and backups (vzdump) set a lock to prevent incompatible concurrent actions on the affected container. Sometimes you need to remove such a lock manually (e.g., after a power
failure).


```
# pct unlock <CTID>
```


> **Caution:**
> Only do this if you are sure the action which set the lock is no longer running.


## See also

- [Linux Containers](_index.md)
- [Software-Defined Network](../ch12-sdn/_index.md)
- [pct CLI Reference](../appendix-a-cli/pct.md)
