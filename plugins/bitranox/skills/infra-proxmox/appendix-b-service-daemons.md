# Service Daemons

*[Main Index](SKILL.md)*


## B.1 pve-firewall - Proxmox VE Firewall Daemon


pve-firewall <COMMAND> [ARGS] [OPTIONS]
pve-firewall compile
Compile and print firewall rules. This is useful for testing.
pve-firewall help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pve-firewall localnet
Print information about local network.
pve-firewall restart
Restart the Proxmox VE firewall service.
pve-firewall simulate [OPTIONS]
Simulate firewall rules. This does not simulates the kernel routing table, but simply assumes that routing
from source zone to destination zone is possible.

- `--dest` <string>
Destination IP address.

- `--dport` <integer>
Destination port.


- `--from` (host|outside|vm\d+|ct\d+|([a-zA-Z][a-zA-Z0-9]{0,9})/(\S+))
(default = outside)
Source zone.

- `--protocol` (tcp|udp) (default = tcp)
Protocol.

- `--source` <string>
Source IP address.

- `--sport` <integer>
Source port.

- `--to` (host|outside|vm\d+|ct\d+|([a-zA-Z][a-zA-Z0-9]{0,9})/(\S+))
(default = host)
Destination zone.

- `--verbose` <boolean> (default = 0)
Verbose output.
pve-firewall start [OPTIONS]
Start the Proxmox VE firewall service.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pve-firewall status
Get firewall status.
pve-firewall stop
Stop the Proxmox VE firewall service. Note, stopping actively removes all Proxmox VE related iptable rules
rendering the host potentially unprotected.


## B.2 pvedaemon - Proxmox VE API Daemon


pvedaemon <COMMAND> [ARGS] [OPTIONS]
pvedaemon help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.

pvedaemon restart
Restart the daemon (or start if not running).
pvedaemon start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pvedaemon status
Get daemon status.
pvedaemon stop
Stop the daemon.


## B.3 pveproxy - Proxmox VE API Proxy Daemon


pveproxy <COMMAND> [ARGS] [OPTIONS]
pveproxy help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pveproxy restart
Restart the daemon (or start if not running).
pveproxy start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pveproxy status
Get daemon status.
pveproxy stop
Stop the daemon.


## B.4 pvestatd - Proxmox VE Status Daemon


pvestatd <COMMAND> [ARGS] [OPTIONS]
pvestatd help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pvestatd restart
Restart the daemon (or start if not running).
pvestatd start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pvestatd status
Get daemon status.
pvestatd stop
Stop the daemon.


## B.5 spiceproxy - SPICE Proxy Service


spiceproxy <COMMAND> [ARGS] [OPTIONS]
spiceproxy help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
spiceproxy restart
Restart the daemon (or start if not running).
spiceproxy start [OPTIONS]
Start the daemon.


- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
spiceproxy status
Get daemon status.
spiceproxy stop
Stop the daemon.


## B.6 pmxcfs - Proxmox Cluster File System


pmxcfs [OPTIONS]
Help Options:

-h, --help
Show help options
Application Options:

-d, --debug
Turn on debug messages

-f, --foreground
Do not daemonize server

-l, --local
Force local mode (ignore corosync.conf, force quorum)
This service is usually started and managed using systemd toolset. The service is called pve-cluster.

systemctl start pve-cluster
systemctl stop pve-cluster
systemctl status pve-cluster


## B.7 pve-ha-crm - Cluster Resource Manager Daemon


pve-ha-crm <COMMAND> [ARGS] [OPTIONS]
pve-ha-crm help [OPTIONS]
Get help about specified command.


- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pve-ha-crm start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pve-ha-crm status
Get daemon status.
pve-ha-crm stop
Stop the daemon.


## B.8 pve-ha-lrm - Local Resource Manager Daemon


pve-ha-lrm <COMMAND> [ARGS] [OPTIONS]
pve-ha-lrm help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pve-ha-lrm start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pve-ha-lrm status
Get daemon status.
pve-ha-lrm stop
Stop the daemon.


## B.9 pvescheduler - Proxmox VE Scheduler Daemon


pvescheduler <COMMAND> [ARGS] [OPTIONS]
pvescheduler help [OPTIONS]
Get help about specified command.

- `--extra-args` <array>
Shows help for a specific command

- `--verbose` <boolean>
Verbose output format.
pvescheduler restart
Restart the daemon (or start if not running).
pvescheduler start [OPTIONS]
Start the daemon.

- `--debug` <boolean> (default = 0)
Debug mode - stay in foreground
pvescheduler status
Get daemon status.
pvescheduler stop
Stop the daemon.

## See also

- [Important Service Daemons](ch18-service-daemons.md)

