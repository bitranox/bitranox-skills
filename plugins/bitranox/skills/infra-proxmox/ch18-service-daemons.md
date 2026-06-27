# Important Service Daemons

*[Main Index](SKILL.md)*


## 18.1 pvedaemon - Proxmox VE API Daemon


This daemon exposes the whole Proxmox VE API on 127.0.0.1:85. It runs as root and has permission
to do all privileged operations.

> **Note:**
> The daemon listens to a local address only, so you cannot access it from outside. The pveproxy
> daemon exposes the API to the outside world.


### 18.1.1 Number of Workers


pvedaemon delegates handling of incoming requests to worker processes. By default, pvedaemon
spawns 3 worker processes, which is sufficient for most workloads. For automation-heavy workloads that
issue a huge volume of API requests and that experience slow request handling or timeouts, the number
of worker processes can be increased by setting MAX_WORKERS in /etc/default/pvedaemon, for
example:
MAX_WORKERS=5
Note that a higher number of worker processes may result in higher CPU usage. The number of worker
processes must be greater than 0 and smaller than 128.
The same setting exists for pveproxy.


## 18.2 pveproxy - Proxmox VE API Proxy Daemon


This daemon exposes the whole Proxmox VE API on TCP port 8006 using HTTPS. It runs as user www-data
and has very limited permissions. Operation requiring more permissions are forwarded to the local pvedaemon.
Requests targeted for other nodes are automatically forwarded to those nodes. This means that you can
manage your whole cluster by connecting to a single Proxmox VE node.


### 18.2.1 Host based Access Control


It is possible to configure “apache2”-like access control lists. Values are read from file /etc/default/pveprox
For example:

ALLOW_FROM="10.0.0.1-10.0.0.5,192.168.0.0/22"
DENY_FROM="all"
POLICY="allow"
IP addresses can be specified using any syntax understood by Net::IP. The name all is an alias for
0/0 and ::/0 (meaning all IPv4 and IPv6 addresses).
The default policy is allow.
Match
Match Allow only
Match Deny only
No match
Match Both Allow & Deny


### 18.2.2 POLICY=deny

allow
deny
deny
deny

POLICY=allow
allow
deny
allow
allow

Listening IP Address

By default the pveproxy and spiceproxy daemons listen on the wildcard address and accept connections from both IPv4 and IPv6 clients.
By setting LISTEN_IP in /etc/default/pveproxy you can control to which IP address the pveproxy
and spiceproxy daemons bind. The IP-address needs to be configured on the system.
Setting the sysctl net.ipv6.bindv6only to the non-default 1 will cause the daemons to only accept
connection from IPv6 clients, while usually also causing lots of other issues. If you set this configuration we
recommend to either remove the sysctl setting, or set the LISTEN_IP to 0.0.0.0 (which will only
allow IPv4 clients).

LISTEN_IP can be used to only to restricting the socket to an internal interface and thus have less exposure
to the public internet, for example:

LISTEN_IP="192.0.2.1"
Similarly, you can also set an IPv6 address:

LISTEN_IP="2001:db8:85a3::1"
Note that if you want to specify a link-local IPv6 address, you need to provide the interface name itself. For
example:

LISTEN_IP="fe80::c463:8cff:feb9:6a4e%vmbr0"


> **Warning:**
> The nodes in a cluster need access to pveproxy for communication, possibly on different subnets. It is not recommended to set LISTEN_IP on clustered systems.


To apply the change you need to either reboot your node or fully restart the pveproxy and spiceproxy
service:

systemctl restart pveproxy.service spiceproxy.service


> **Note:**
> Unlike reload, a restart of the pveproxy service can interrupt some long-running worker processes,
> for example a running console or shell from a virtual guest. So, please use a maintenance window to bring
> this change in effect.


### 18.2.3 SSL Cipher Suite


You can define the cipher list in /etc/default/pveproxy via the CIPHERS (TLS ⇐ 1.2) and CIPHERSUITE
(TLS >= 1.3) keys. For example

CIPHERS="ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384: ←ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE- ←ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA- ←AES256-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES128-SHA256: ←ECDHE-RSA-AES128-SHA256"
CIPHERSUITES="TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256: ←TLS_AES_128_GCM_SHA256"
Above is the default. See the ciphers(1) man page from the openssl package for a list of all available options.
Additionally, you can set the client to choose the cipher used in /etc/default/pveproxy (default is
the first cipher in the list available to both client and pveproxy):

HONOR_CIPHER_ORDER=0


### 18.2.4 Supported TLS versions


The insecure SSL versions 2 and 3 are unconditionally disabled for pveproxy. TLS versions below 1.1 are disabled by default on recent OpenSSL versions, which is honored by pveproxy (see /etc/ssl/openssl.cnf)
To disable TLS version 1.2 or 1.3, set the following in /etc/default/pveproxy:

DISABLE_TLS_1_2=1
or, respectively:

DISABLE_TLS_1_3=1


> **Note:**
> Unless there is a specific reason to do so, it is not recommended to manually adjust the supported TLS
> versions.


### 18.2.5 Diffie-Hellman Parameters


You can define the used Diffie-Hellman parameters in /etc/default/pveproxy by setting DHPARAMS
to the path of a file containing DH parameters in PEM format, for example

DHPARAMS="/path/to/dhparams.pem"
If this option is not set, the built-in skip2048 parameters will be used.

> **Note:**
> DH parameters are only used if a cipher suite utilizing the DH key exchange algorithm is negotiated.


### 18.2.6 Alternative HTTPS certificate


You can change the certificate used to an external one or to one obtained via ACME.

pveproxy uses /etc/pve/local/pveproxy-ssl.pem and /etc/pve/local/pveproxy-ssl.key,
if present, and falls back to /etc/pve/local/pve-ssl.pem and /etc/pve/local/pve-ssl.key.
The private key may not use a passphrase.
It is possible to override the location of the certificate private key /etc/pve/local/pveproxy-ssl.key
by setting TLS_KEY_FILE in /etc/default/pveproxy, for example:

TLS_KEY_FILE="/secrets/pveproxy.key"


> **Note:**
> The included ACME integration does not honor this setting.


See the Host System Administration chapter of the documentation for details.


### 18.2.7 Response Compression


By default pveproxy uses gzip HTTP-level compression for compressible content, if the client supports it.
This can disabled in /etc/default/pveproxy

COMPRESSION=0


### 18.2.8 Real Client IP Logging


By default, pveproxy logs the IP address of the client that sent the request. In cases where a proxy server
is in front of pveproxy, it may be desirable to log the IP of the client making the request instead of the
proxy IP.
To enable processing of a HTTP header set by the proxy for logging purposes, set PROXY_REAL_IP_HEADER
to the name of the header to retrieve the client IP from. For example:

PROXY_REAL_IP_HEADER="X-Forwarded-For"


Any invalid values passed in this header will be ignored.
The default behavior is log the value in this header on all incoming requests. To define a list of proxy servers
that should be trusted to set the above HTTP header, set PROXY_REAL_IP_ALLOW_FROM, for example:

PROXY_REAL_IP_ALLOW_FROM="192.168.0.2"
The PROXY_REAL_IP_ALLOW_FROM setting also supports values similar to the ALLOW_FROM and
DENY_FROM settings.
IP addresses can be specified using any syntax understood by Net::IP. The name all is an alias for
0/0 and ::/0 (meaning all IPv4 and IPv6 addresses).


### 18.2.9 Number of Workers


pveproxy delegates handling of incoming requests to worker processes. By default, pveproxy spawns
3 worker processes, which is sufficient for most workloads. For automation-heavy workloads that issue a
huge volume of API requests and that experience slow request handling or timeouts, the number of worker
processes can be increased by setting MAX_WORKERS in /etc/default/pveproxy, for example:

MAX_WORKERS=5
Note that a higher number of worker processes may result in higher CPU usage. The number of worker
processes must be greater than 0 and smaller than 128.
The same setting exists for pvedaemon.


## 18.3 pvestatd - Proxmox VE Status Daemon


This daemon queries the status of VMs, storages and containers at regular intervals. The result is sent to all
nodes in the cluster.


## 18.4 spiceproxy - SPICE Proxy Service


SPICE (the Simple Protocol for Independent Computing Environments) is an open remote computing solution, providing client access to remote displays and devices (e.g. keyboard, mouse, audio). The main use
case is to get remote access to virtual machines and container.
This daemon listens on TCP port 3128, and implements an HTTP proxy to forward CONNECT request from
the SPICE client to the correct Proxmox VE VM. It runs as user www-data and has very limited permissions.


### 18.4.1 Host based Access Control


It is possible to configure "apache2" like access control lists. Values are read from file /etc/default/pveprox
See pveproxy documentation for details.


## 18.5 pvescheduler - Proxmox VE Scheduler Daemon


This daemon is responsible for starting jobs according to the schedule, such as replication and vzdump jobs.
For vzdump jobs, it gets its configuration from the file /etc/pve/jobs.cfg

## See also

- [Certificate Management](ch03-host-admin/certificate-management.md)
- [Service Daemons (Appendix B)](appendix-b-service-daemons.md)

