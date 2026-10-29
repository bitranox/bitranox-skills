# PVE tasks: when the CLI waits, polling a task yourself, and filing your own task

Every state-changing PVE operation runs as a TASK, identified by a UPID
(`UPID:<node>:<pid>:<pstart>:<starttime>:<type>:<id>:<user>:`), with a log and a final status in
the task list. Two things about tasks are easy to get wrong: how long a CLI call waits for one,
and what a task you file yourself will show.

Measured on pve-manager 9.2.21; re-check on another release before building on a detail.

## The CLI blocks until the task ends

`qm start`, `qm shutdown`, `qm stop` and `pvesh create /nodes/<node>/qemu/<vmid>/status/<action>`
run their worker SYNCHRONOUSLY when called from the command line: `fork_worker` in
`PVE::RESTEnvironment` waits for the worker in a CLI environment. So the command returns only
when the task has finished, and a `--timeout` you pass is the task's own timeout, not a bound on
how long you wait. The API over HTTPS returns the UPID at once instead.

The trap: `qm shutdown <vmid> --timeout 90 || qm stop <vmid>` cannot watch the guest while it
waits. After 90 s the shutdown task fails and the `qm stop` hard-stops a guest that may have been
in the middle of a clean shutdown - for a Windows guest that is a dirty NTFS volume, baked into
whatever image you take from it next.

To issue the request and decide yourself how long to wait:

```bash
since=$(date +%s)
setsid -f qm shutdown <vmid> --forceStop 0 --timeout 600       # detached: returns at once
pvesh get /nodes/<node>/tasks --vmid <vmid> --since "$since" --output-format json
#   -> pick the qmshutdown entry's "upid"
pvesh get /nodes/<node>/tasks/<upid>/status --output-format json
#   -> "status": "running" | "stopped"; when stopped, "exitstatus" is "OK" or the error text
pvesh delete /nodes/<node>/tasks/<upid>                         # cancel it, if you decide to
```

`setsid -f` forces the fork, so the call returns whatever shell runs it (see `bitranox:compuse-bash`
for why a plain `setsid` may or may not wait). Watch your own progress signal in between (guest
agent ping, console, I/O) and decide on a hard stop only when the guest has really stopped
progressing.

**`qm status` reading `stopped` is not "task done".** PVE holds the VM's config lock through the
post-stop cleanup, so the next `qm` on that vmid issued at that moment can fail on the lock. Wait
for the TASK to reach `stopped` (above), then run the next command.

## Filing your own task from code outside a PVE worker

A tool that does work on behalf of PVE (a hook, a helper started by a hookscript) can file a real
task, so the result shows in the GUI's task list and in `pvenode task list`. In Perl, as root:

```perl
#!/usr/bin/perl
use strict;
use warnings;
use PVE::RPCEnvironment;
use PVE::RESTEnvironment qw(log_warn);

my $rpcenv = PVE::RPCEnvironment->setup_default_cli_env();
$rpcenv->fork_worker('mytask', '100', 'root@pam', sub {
    print "doing the work\n";                 # goes to the task log
    log_warn("something worth flagging\n");   # counted as a warning
    die "the reason it failed\n";             # becomes the task status, verbatim
});
```

- **Launch it detached, keep the default synchronous mode.** Start the helper with
  `systemd-run --collect --no-block <helper>`; no TTY is needed. Passing `background => 1` to
  `fork_worker` instead lets the worker be killed along with the transient unit, and the task then
  ends `received interrupt`.
- **The status is the full `die` text, untruncated.** End it in `"\n"`, or Perl appends
  ` at <file> line <N>.` to what the user reads.
- **Warnings and a `die` do not combine.** With warnings followed by a `die`, the status shows
  only the die text and the warning count is lost. With N `log_warn` calls and no `die`, the status
  is `WARNINGS: N`; a multi-line `log_warn` counts once.
- **`pvenode task list` prints a literal `ERROR` for every failed task.** Read the reason with
  `pvenode task status <upid>` or `pvesh get /nodes/<node>/tasks/<upid>/status`.
- **Type and id must not contain a space, a colon or a slash**: they are fields of the UPID, and
  `PVE/UPID.pm` cannot decode one that does.
- **The GUI's description.** A type that is not in PVE's task description table renders as
  `<type> <id>` (`format_task_description` in `proxmoxlib.js`). The `VM <id> - <Action>` form
  needs a stock type (`qmstart`, `qmrollback`, `vzdump`, ...); the table lives in a
  package-owned file (`pvemanagerlib.js`), which an update overwrites, so do not patch it.
- **A child of another worker cannot warn into it.** A `log_warn` from a process that the
  `qmstart` worker runs with `run_fork` (a wrapper around the kvm binary, for example) never
  reaches the parent task's status.
