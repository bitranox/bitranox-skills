# Proxmox VE Firewall

*[Main Index](../SKILL.md)*


Proxmox VE Firewall provides an easy way to protect your IT infrastructure. You can setup firewall rules for
all hosts inside a cluster, or define rules for virtual machines and containers. Features like firewall macros,
security groups, IP sets and aliases help to make that task easier.
While all configuration is stored on the cluster file system, the iptables-based firewall service runs on
each cluster node, and thus provides full isolation between virtual machines. The distributed nature of this
system also provides much higher bandwidth than a central firewall solution.
The firewall has full support for IPv4 and IPv6. IPv6 support is fully transparent, and we filter traffic for both
protocols by default. So there is no need to maintain a different set of rules for IPv6.


## 13.1 Directions & Zones


The Proxmox VE firewall groups the network into multiple logical zones. You can define rules for each zone
independently. Depending on the zone, you can define rules for incoming, outgoing or forwarded traffic.


### 13.1.1 Directions


There are 3 directions that you can choose from when defining rules for a zone:

In
Traffic that is arriving in a zone.
Out
Traffic that is leaving a zone.
Forward
Traffic that is passing through a zone. In the host zone this can be routed traffic (when the host is
acting as a gateway or performing NAT). At a VNet-level this affects all traffic that is passing by a VNet,
including traffic from/to bridged network interfaces.


> **Important:**
> Creating rules for forwarded traffic is currently only possible when using the new nftables-based
> proxmox-firewall. Any forward rules will be ignored by the stock pve-firewall and have no
> effect!


### 13.1.2 Zones


There are 3 different zones that you can define firewall rules for:

Host
Traffic going from/to a host, or traffic that is forwarded by a host. You can define rules for this zone
either at the datacenter level or at the host level. Rules at host level take precedence over rules at
datacenter level.
VM
Traffic going from/to a VM or CT. You cannot define rules for forwarded traffic, only for incoming /
outgoing traffic.
VNet
Traffic passing through a SDN VNet, either from guest to guest or from host to guest and vice-versa.
Since this traffic is always forwarded traffic, it is only possible to create rules with direction forward.

> **Important:**
> Creating rules on a VNet-level is currently only possible when using the new nftables-based
> proxmox-firewall. Any VNet-level rules will be ignored by the stock pve-firewall and have
> no effect!


## 13.2 Configuration Files


All firewall related configuration is stored on the proxmox cluster file system. So those files are automatically
distributed to all cluster nodes, and the pve-firewall service updates the underlying iptables rules
automatically on changes.
You can configure anything using the GUI (i.e. Datacenter → Firewall, or on a Node → Firewall), or you
can edit the configuration files directly using your preferred editor.
Firewall configuration files contain sections of key-value pairs. Lines beginning with a # and blank lines are
considered comments. Sections start with a header line containing the section name enclosed in [ and ].


### 13.2.1 Cluster Wide Setup


The cluster-wide firewall configuration is stored at:

/etc/pve/firewall/cluster.fw

The configuration can contain the following sections:

[OPTIONS]
This is used to set cluster-wide firewall options.

ebtables: <boolean> (default = 1)
Enable ebtables rules cluster wide.

enable: <integer> (0 - N) (default = 0)
Enable or disable the firewall cluster wide.

log_ratelimit: [enable=]<1|0> [,burst=<integer>] [,rate=<rate>]
Log ratelimiting settings

burst=<integer> (0 - N) (default = 5)
Initial burst of packages which will always get logged before the rate is applied

enable=<boolean> (default = 1)
Enable or disable log rate limiting

rate=<rate> (default = 1/second)
Frequency with which the burst bucket gets refilled

policy_forward: <ACCEPT | DROP>
Forward policy.

policy_in: <ACCEPT | DROP | REJECT>
Input policy.

policy_out: <ACCEPT | DROP | REJECT>
Output policy.

[RULES]
This sections contains cluster-wide firewall rules for all nodes.

[IPSET <name>]
Cluster wide IP set definitions.

[GROUP <name>]
Cluster wide security group definitions.

[ALIASES]
Cluster wide Alias definitions.


Enabling the Firewall
The firewall is completely disabled by default, so you need to set the enable option here:

[OPTIONS]
# enable firewall (cluster-wide setting, default is disabled)
enable: 1


> **Important:**
> If you enable the firewall, traffic to all hosts is blocked by default. Only exceptions is WebGUI(8006)
> and ssh(22) from your local network.


If you want to administrate your Proxmox VE hosts from remote, you need to create rules to allow traffic from
those remote IPs to the web GUI (port 8006). You may also want to allow ssh (port 22), and maybe SPICE
(port 3128).

> **Tip:**
> Please open a SSH connection to one of your Proxmox VE hosts before enabling the firewall. That way
> you still have access to the host if something goes wrong .


To simplify that task, you can instead create an IPSet called “management”, and add all remote IPs there.
This creates all required firewall rules to access the GUI from remote.


### 13.2.2 Host Specific Configuration


Host related configuration is read from:

/etc/pve/nodes/<nodename>/host.fw
This is useful if you want to overwrite rules from cluster.fw config. You can also increase log verbosity,
and set netfilter related options. The configuration can contain the following sections:

[OPTIONS]
This is used to set host related firewall options.

enable: <boolean> (default = 1)
Enable host firewall rules.

log_level_forward: <alert | crit | debug | emerg | err | info |
nolog | notice | warning>
Log level for forwarded traffic.

log_level_in: <alert | crit | debug | emerg | err | info | nolog |
notice | warning>
Log level for incoming traffic.


log_level_out: <alert | crit | debug | emerg | err | info | nolog |
notice | warning>
Log level for outgoing traffic.

log_nf_conntrack: <boolean> (default = 0)
Enable logging of conntrack information.

ndp: <boolean> (default = 1)
Enable NDP (Neighbor Discovery Protocol).

nf_conntrack_allow_invalid: <boolean> (default = 0)
Allow invalid packets on connection tracking.

nf_conntrack_helpers: <string> (default = ``)
Enable conntrack helpers for specific protocols. Supported protocols: amanda, ftp, irc, netbios-ns,
pptp, sane, sip, snmp, tftp

nf_conntrack_max: <integer> (32768 - N) (default = 262144)
Maximum number of tracked connections.

nf_conntrack_tcp_timeout_established: <integer> (7875 - N) (default =
432000)
Conntrack established timeout.

nf_conntrack_tcp_timeout_syn_recv: <integer> (30 - 60) (default = 60)
Conntrack syn recv timeout.

nftables: <boolean> (default = 0)
Enable nftables based firewall (tech preview)

nosmurfs: <boolean>
Enable SMURFS filter.

protection_synflood: <boolean> (default = 0)
Enable synflood protection

protection_synflood_burst: <integer> (default = 1000)
Synflood protection rate burst by ip src.

protection_synflood_rate: <integer> (default = 200)
Synflood protection rate syn/sec by ip src.

smurf_log_level: <alert | crit | debug | emerg | err | info | nolog
| notice | warning>
Log level for SMURFS filter.


tcp_flags_log_level: <alert | crit | debug | emerg | err | info |
nolog | notice | warning>
Log level for illegal tcp flags filter.

tcpflags: <boolean> (default = 0)
Filter illegal combinations of TCP flags.

[RULES]
This sections contains host specific firewall rules.


### 13.2.3 VM/Container Configuration


VM firewall configuration is read from:

/etc/pve/firewall/<VMID>.fw
and contains the following data:

[OPTIONS]
This is used to set VM/Container related firewall options.

dhcp: <boolean> (default = 0)
Enable DHCP.

enable: <boolean> (default = 0)
Enable/disable firewall rules.

ipfilter: <boolean>
Enable default IP filters. This is equivalent to adding an empty ipfilter-net<id> ipset for every interface.
Such ipsets implicitly contain sane default restrictions such as restricting IPv6 link local addresses to
the one derived from the interface’s MAC address. For containers the configured IP addresses will be
implicitly added.

log_level_in: <alert | crit | debug | emerg | err | info | nolog |
notice | warning>
Log level for incoming traffic.

log_level_out: <alert | crit | debug | emerg | err | info | nolog |
notice | warning>
Log level for outgoing traffic.

macfilter: <boolean> (default = 1)
Enable/disable MAC address filter.

ndp: <boolean> (default = 1)
Enable NDP (Neighbor Discovery Protocol).


policy_in: <ACCEPT | DROP | REJECT>
Input policy.

policy_out: <ACCEPT | DROP | REJECT>
Output policy.

radv: <boolean>
Allow sending Router Advertisement.

[RULES]
This sections contains VM/Container firewall rules.

[IPSET <name>]
IP set definitions.

[ALIASES]
IP Alias definitions.

Enabling the Firewall for VMs and Containers
Each virtual network device has its own firewall enable flag. So you can selectively enable the firewall for
each interface. This is required in addition to the general firewall enable option.


### 13.2.4 VNet Configuration


VNet related configuration is read from:

/etc/pve/sdn/firewall/<vnet_name>.fw
This can be used for setting firewall configuration globally on a VNet level, without having to set firewall rules
for each VM inside the VNet separately. It can only contain rules for the FORWARD direction, since there
is no notion of incoming or outgoing traffic. This affects all traffic travelling from one bridge port to another,
including the host interface.


> **Warning:**
> This feature is currently only available for the new nftables-based proxmox-firewall


Since traffic passing the FORWARD chain is bi-directional, you need to create rules for both directions if you
want traffic to pass both ways. For instance if HTTP traffic for a specific host should be allowed, you would
need to create the following rules:

FORWARD ACCEPT -dest 10.0.0.1 -dport 80
FORWARD ACCEPT -source 10.0.0.1 -sport 80


[OPTIONS]
This is used to set VNet related firewall options.

enable: <boolean> (default = 0)
Enable/disable firewall rules.

log_level_forward: <alert | crit | debug | emerg | err | info |
nolog | notice | warning>
Log level for forwarded traffic.

policy_forward: <ACCEPT | DROP>
Forward policy.

[RULES]
This section contains VNet specific firewall rules.


## 13.3 Firewall Rules


Firewall rules consists of a direction (IN, OUT or FORWARD) and an action (ACCEPT, DENY, REJECT). You
can also specify a macro name. Macros contain predefined sets of rules and options. Rules can be disabled
by prefixing them with |.
Firewall rules syntax

[RULES]
DIRECTION ACTION [OPTIONS]
|DIRECTION ACTION [OPTIONS] # disabled rule
DIRECTION MACRO(ACTION) [OPTIONS] # use predefined macro
The following options can be used to refine rule matches.

- `--dest` <string>
Restrict packet destination address. This can refer to a single IP address, an IP set (+ipsetname) or
an IP alias definition. You can also specify an address range like 20.34.101.207-201.3.9.99, or a list
of IP addresses and networks (entries are separated by comma). Please do not mix IPv4 and IPv6
addresses inside such lists.

- `--dport` <string>
Restrict TCP/UDP destination port. You can use service names or simple numbers (0-65535), as
defined in /etc/services. Port ranges can be specified with \d+:\d+, for example 80:85, and you can
use comma separated list to match several ports or ranges.

- `--icmp-type` <string>
Specify icmp-type. Only valid if proto equals icmp or icmpv6/ipv6-icmp.


- `--iface` <string>
Network interface name. You have to use network configuration key names for VMs and containers
(net\d+). Host related rules can use arbitrary strings.

- `--log` <alert | crit | debug | emerg | err | info | nolog | notice |
warning>
Log level for firewall rule.

- `--proto` <string>
IP protocol. You can use protocol names (tcp/udp) or simple numbers, as defined in /etc/protocols.

- `--source` <string>
Restrict packet source address. This can refer to a single IP address, an IP set (+ipsetname) or an
IP alias definition. You can also specify an address range like 20.34.101.207-201.3.9.99, or a list
of IP addresses and networks (entries are separated by comma). Please do not mix IPv4 and IPv6
addresses inside such lists.

- `--sport` <string>
Restrict TCP/UDP source port. You can use service names or simple numbers (0-65535), as defined
in /etc/services. Port ranges can be specified with \d+:\d+, for example 80:85, and you can use comma
separated list to match several ports or ranges.
Here are some examples:

[RULES]
IN SSH(ACCEPT) -i net0
IN SSH(ACCEPT) -i net0 # a comment
IN SSH(ACCEPT) -i net0 -source 192.168.2.192 # only allow SSH from ←192.168.2.192
IN SSH(ACCEPT) -i net0 -source 10.0.0.1-10.0.0.10 # accept SSH for IP range
IN SSH(ACCEPT) -i net0 -source 10.0.0.1,10.0.0.2,10.0.0.3 #accept ssh for ←IP list
IN SSH(ACCEPT) -i net0 -source +mynetgroup # accept ssh for ipset ←mynetgroup
IN SSH(ACCEPT) -i net0 -source myserveralias #accept ssh for alias ←myserveralias
|IN SSH(ACCEPT) -i net0 # disabled rule
IN DROP # drop all incoming packages
OUT ACCEPT # accept all outgoing packages


## 13.4 Security Groups


A security group is a collection of rules, defined at cluster level, which can be used in all VMs’ rules. For
example you can define a group named “webserver” with rules to open the http and https ports.


# /etc/pve/firewall/cluster.fw
[group webserver]
IN ACCEPT -p tcp -dport 80
IN ACCEPT -p tcp -dport 443
Then, you can add this group to a VM’s firewall

# /etc/pve/firewall/<VMID>.fw
[RULES]
GROUP webserver


## See also

- [Firewall: IP Aliases, Sets, Services and Advanced Topics](firewall-advanced.md)
- [Software-Defined Network](../ch12-sdn/_index.md)
- [User Management](../ch14-user-management/_index.md)
- [Firewall Macro Definitions](../appendix-f-firewall-macros.md)
