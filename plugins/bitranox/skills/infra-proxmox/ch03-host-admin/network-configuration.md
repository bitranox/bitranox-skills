# Network Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


```
# apt install intel-microcode=3.202305*
...
Selected version '3.20230512.1' (Debian:12.1/stable [amd64]) for 'intel- ←microcode'
...
dpkg: warning: downgrading intel-microcode from 3.20230808.1~deb12u1 to ←3.20230512.1
...
intel-microcode: microcode will be updated at next boot
...
Make sure (again) that the host can be rebooted safely. To apply an older microcode potentially included in
the microcode package for your CPU type, reboot now.
Tip
It makes sense to hold the downgraded package for a while and try more recent versions again at a
later time. Even if the package version is the same in the future, system updates may have fixed the
experienced problem in the meantime.

# apt-mark hold intel-microcode
intel-microcode set on hold.
# apt-mark unhold intel-microcode
# apt update
# apt full-upgrade
```


## 3.4 Network Configuration


Proxmox VE is using the Linux network stack. This provides a lot of flexibility on how to set up the network
on the Proxmox VE nodes. The configuration can be done either via the GUI, or by manually editing the file
/etc/network/interfaces, which contains the whole network configuration. The interfaces(5)
manual page contains the complete format description. All Proxmox VE tools try hard to keep direct user
modifications, but using the GUI is still preferable, because it protects you from errors.
A Linux bridge interface (commonly called vmbrX ) is needed to connect guests to the underlying physical
network. It can be thought of as a virtual switch which the guests and physical interfaces are connected
to. This section provides some examples on how the network can be set up to accommodate different use
cases like redundancy with a bond, vlans or routed and NAT setups.
The Software Defined Network is an option for more complex virtual networks in Proxmox VE clusters.

> **Warning:**
> It’s discouraged to use the traditional Debian tools ifup and ifdown if unsure, as they have some
> pitfalls like interrupting all guest traffic on ifdown vmbrX but not reconnecting those guest again
> when doing ifup on the same bridge later.


### 3.4.1 Apply Network Changes


Proxmox VE does not write changes directly to /etc/network/interfaces. Instead, we write into a
temporary file called /etc/network/interfaces.new, this way you can do many related changes at
once. This also allows to ensure your changes are correct before applying, as a wrong network configuration
may render a node inaccessible.

Live-Reload Network with ifupdown2
With the recommended ifupdown2 package (default for new installations since Proxmox VE 7.0), it is possible
to apply network configuration changes without a reboot. If you change the network configuration via the GUI,
you can click the Apply Configuration button. This will move changes from the staging interfaces.new
file to /etc/network/interfaces and apply them live.
If you made manual changes directly to the /etc/network/interfaces file, you can apply them by
running ifreload -a

> **Note:**
> If you installed Proxmox VE on top of Debian, or upgraded to Proxmox VE 7.0 from an older Proxmox VE
> installation, make sure ifupdown2 is installed: apt install ifupdown2


Reboot Node to Apply
Another way to apply a new network configuration is to reboot the node. In that case the systemd service
pvenetcommit will activate the staging interfaces.new file before the networking service will
apply that configuration.


### 3.4.2 Naming Conventions


We currently use the following naming conventions for device names:

- Ethernet devices: en*, systemd network interface names. This naming scheme is used for new Proxmox
VE installations since version 5.0.

- Ethernet devices: eth[N], where 0 ≤ N (eth0, eth1, . . . ) This naming scheme is used for Proxmox
VE hosts which were installed before the 5.0 release. When upgrading to 5.0, the names are kept as-is.

- Bridge names: Commonly vmbr[N], where 0 ≤ N ≤ 4094 (vmbr0 - vmbr4094), but you can use any
alphanumeric string that starts with a character and is at most 10 characters long.

- Bonds: bond[N], where 0 ≤ N (bond0, bond1, . . . )
- VLANs: Simply add the VLAN number to the device name, separated by a period (eno1.50, bond1.30)
This makes it easier to debug networks problems, because the device name implies the device type.


Systemd Network Interface Names
Systemd defines a versioned naming scheme for network device names. The scheme uses the two-character
prefix en for Ethernet network devices. The next characters depends on the device driver, device location
and other attributes. Some possible patterns are:

- o<index>[n<phys_port_name>|d<dev_port>] — devices on board
- s<slot>[f<function>][n<phys_port_name>|d<dev_port>] — devices by hotplug id
- [P<domain>]p<bus>s<slot>[f<function>][n<phys_port_name>|d<dev_port>] —
devices by bus id

- x<MAC> — devices by MAC address
Some examples for the most common patterns are:

- eno1 — is the first on-board NIC
- enp3s0f1 — is function 1 of the NIC on PCI bus 3, slot 0
For a full list of possible device name patterns, see the systemd.net-naming-scheme(7) manpage.
A new version of systemd may define a new version of the network device naming scheme, which it then
uses by default. Consequently, updating to a newer systemd version, for example during a major Proxmox
VE upgrade, can change the names of network devices and require adjusting the network configuration. To
avoid name changes due to a new version of the naming scheme, you can manually pin a particular naming
scheme version (see below).
However, even with a pinned naming scheme version, network device names can still change due to kernel or
driver updates. In order to avoid name changes for a particular network device altogether, you can manually
override its name using a link file (see below).
For more information on network interface names, see Predictable Network Interface Names.

Pinning a specific naming scheme version

You can pin a specific version of the naming scheme for network devices by adding the net.naming-scheme=<
parameter to the kernel command line. For a list of naming scheme versions, see the systemd.net-namingscheme(7) manpage.
For example, to pin the version v252, which is the latest naming scheme version for a fresh Proxmox VE

## 8.0 installation, add the following kernel command-line parameter:


net.naming-scheme=v252
See also this section on editing the kernel command line. You need to reboot for the changes to take effect.


Overriding Network Device Names
Using the pve-network-interface-pinning Tool
Proxmox VE provides a tool for automatically generating .link files for overriding the name of network devices.
It also automatically replaces the occurences of the old interface name in the following files:

- /etc/network/interfaces
- /etc/pve/nodes/<nodename>/host.fw
- /etc/pve/sdn/controllers.cfg
- /etc/pve/sdn/fabrics.cfg

> **Note:**
> Since the generated mapping is local to the node it is generated on, interface names contained in the Firewall Datacenter configuration (/etc/pve/firewall/cluster.fw) are not automatically updated.


The generated link files are stored in /usr/local/lib/systemd/network. For the configuration
files a new file will be generated in the same place with a .new suffix. This way you can inspect the
changes made to the configuration by using diff (or another diff viewer of your choice):

diff -y /etc/network/interfaces /etc/network/interfaces.new
If you see any problematic changes or want to revert the changes made by the pinning tool before rebooting,
simply delete all .new files and the respective link files from /usr/local/lib/systemd/network.
The following command will generate a .link file for all physical network interfaces that do not yet have a
.link file and update selected Proxmox VE configuration files (see above). The generated names will use the
default prefix nic, so the resulting interface names will be nic1, nic2, . . .

pve-network-interface-pinning generate
You can override the default prefix with the --prefix flag:

pve-network-interface-pinning generate --prefix myprefix
It is also possible to pin only a specific interface:

pve-network-interface-pinning generate --interface enp1s0
When pinning a specific interface, you can specify the exact name that the interface should be pinned to:

pve-network-interface-pinning generate --interface enp1s0 --target-name
if42

←-

In order to apply the changes made by pve-network-interface-pinning to the network configuration, the node needs to be rebooted.


Manually Creating .Link Files
You can manually assign a name to a particular network device using a custom systemd.link file. This
overrides the name that would be assigned according to the latest network device naming scheme. This
way, you can avoid naming changes due to kernel updates, driver updates or newer versions of the naming
scheme.
Custom link files should be placed in /etc/systemd/network/ and named <n>-<id>.link, where
n is a priority smaller than 99 and id is some identifier. A link file has two sections: [Match] determines
which interfaces the file will apply to; [Link] determines how these interfaces should be configured, including their naming.
To assign a name to a particular network device, you need a way to uniquely and permanently identify that device in the [Match] section. One possibility is to match the device’s MAC address using the MACAddress
option, as it is unlikely to change.
The [Match] section should also contain a Type option to make sure it only matches the expected physical interface, and not bridge/bond/VLAN interfaces with the same MAC address. In most setups, Type
should be set to ether to match only Ethernet devices, but some setups may require other choices. See
the systemd.link(5) manpage for more details.
Then, you can assign a name using the Name option in the [Link] section.
Link files are copied to the initramfs, so it is recommended to refresh the initramfs after adding,
modifying, or removing a link file:

# update-initramfs -u -k all
For example, to assign the name enwan0 to the Ethernet device with MAC address aa:bb:cc:dd:ee:ff,
create a file /etc/systemd/network/10-enwan0.link with the following contents:

[Match]
MACAddress=aa:bb:cc:dd:ee:ff
Type=ether
[Link]
Name=enwan0
Do not forget to adjust /etc/network/interfaces to use the new name, and refresh your initramfs
as described above. You need to reboot the node for the change to take effect.

> **Note:**
> It is recommended to assign a name starting with en or eth so that Proxmox VE recognizes the interface
> as a physical network device which can then be configured via the GUI. Also, you should ensure that the
> name will not clash with other interface names in the future. One possibility is to assign a name that does
> not match any name pattern that systemd uses for network interfaces (see above), such as enwan0 in
> the example above.


For more information on link files, see the systemd.link(5) manpage.


### 3.4.3 Choosing a network configuration


Depending on your current network organization and your resources you can choose either a bridged, routed,
or masquerading networking setup.


Proxmox VE server in a private LAN, using an external gateway to reach the internet
The Bridged model makes the most sense in this case, and this is also the default mode on new Proxmox
VE installations. Each of your Guest system will have a virtual interface attached to the Proxmox VE bridge.
This is similar in effect to having the Guest network card directly connected to a new switch on your LAN, the
Proxmox VE host playing the role of the switch.
Proxmox VE server at hosting provider, with public IP ranges for Guests
For this setup, you can use either a Bridged or Routed model, depending on what your provider allows.
Proxmox VE server at hosting provider, with a single public IP address
In that case the only way to get outgoing network accesses for your guest systems is to use Masquerading.
For incoming network access to your guests, you will need to configure Port Forwarding.
For further flexibility, you can configure VLANs (IEEE 802.1q) and network bonding, also known as "link
aggregation". That way it is possible to build complex and flexible virtual networks.


### 3.4.4 Default Configuration Using a Bridge


Top of Rack Switch
1

eno1

Gateway, DHCP

#### 192.168.10.1 2


3

eno1

eno1

vmbr0

vmbr0

192.168.10.2/24

192.168.10.3/24

tap100i0

tap200i0

ens18

ens18

tap201i0

ens18

VM 100

VM 200

VM 201


#### 192.168.10.100 192.168.10.200


#### 192.168.10.201 Node: proxmox1


Node: proxmox2

Bridges are like physical network switches implemented in software. All virtual guests can share a single
bridge, or you can create multiple bridges to separate network domains. Each host can have up to 4094
bridges.
The installation program creates a single bridge named vmbr0, which is connected to the first Ethernet
card. The corresponding configuration in /etc/network/interfaces might look like this:


auto lo
iface lo inet loopback
iface eno1 inet manual
auto vmbr0
iface vmbr0 inet static
address 192.168.10.2/24
gateway 192.168.10.1
bridge-ports eno1
bridge-stp off
bridge-fd 0
Virtual machines behave as if they were directly connected to the physical network. The network, in turn,
sees each virtual machine as having its own MAC, even though there is only one network cable connecting
all of these VMs to the network.


### 3.4.5 Routed Configuration


Most hosting providers do not support the above setup. For security reasons, they disable networking as
soon as they detect multiple MAC addresses on a single interface.

> **Tip:**
> Some providers allow you to register additional MACs through their management interface. This avoids
> the problem, but can be clumsy to configure because you need to register a MAC for each of your VMs.


You can avoid the problem by “routing” all traffic via a single interface. This makes sure that all network
packets use the same MAC address.


Provider Gateway

#### 198.51.100.1 ip_forward = 1

proxy_arp = 1

vmbr0
203.0.113.17/28

eno0

198.51.100.5/29

tap100i0

ens18

ens18

ens18

VM 100

VM 101

VM 102


#### 203.0.113.18 203.0.113.19


#### 203.0.113.20 Node: proxmox

A common scenario is that you have a public IP (assume 198.51.100.5 for this example), and an additional IP block for your VMs (203.0.113.16/28). We recommend the following setup for such situations:

auto lo
iface lo inet loopback
auto eno0
iface eno0 inet static
address 198.51.100.5/29
gateway 198.51.100.1
post-up echo 1 > /proc/sys/net/ipv4/ip_forward
post-up echo 1 > /proc/sys/net/ipv4/conf/eno0/proxy_arp

auto vmbr0
iface vmbr0 inet static
address 203.0.113.17/28
bridge-ports none
bridge-stp off
bridge-fd 0


### 3.4.6 Masquerading (NAT) with iptables


Masquerading allows guests having only a private IP address to access the network by using the host IP
address for outgoing traffic. Each outgoing packet is rewritten by iptables to appear as originating from
the host, and responses are rewritten accordingly to be routed to the original sender.

auto lo


iface lo inet loopback
auto eno1
#real IP address
iface eno1 inet static
address 198.51.100.5/24
gateway 198.51.100.1
auto vmbr0
#private sub network
iface vmbr0 inet static
address 10.10.10.1/24
bridge-ports none
bridge-stp off
bridge-fd 0
post-up
echo 1 > /proc/sys/net/ipv4/ip_forward
post-up
iptables -t nat -A POSTROUTING -s '10.10.10.0/24' -o eno1 ←-j MASQUERADE
post-down iptables -t nat -D POSTROUTING -s '10.10.10.0/24' -o eno1 ←-j MASQUERADE


> **Note:**
> In some masquerade setups with firewall enabled, conntrack zones might be needed for outgoing connections. Otherwise the firewall could block outgoing connections since they will prefer the POSTROUTING
> of the VM bridge (and not MASQUERADE).


Adding these lines in the /etc/network/interfaces can fix this problem:

post-up
iptables -t raw -I PREROUTING -i fwbr+ -j CT --zone 1
post-down iptables -t raw -D PREROUTING -i fwbr+ -j CT --zone 1
For more information about this, refer to the following links:
Netfilter Packet Flow
Patch on netdev-list introducing conntrack zones
Blog post with a good explanation by using TRACE in the raw table


## See also

- [Network Bonding, VLANs and more](network-bonding-vlans.md)
- [Software-Defined Network](../ch12-sdn/_index.md)
- [Firewall](../ch13-firewall/_index.md)
