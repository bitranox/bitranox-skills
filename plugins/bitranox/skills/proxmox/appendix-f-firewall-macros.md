# Firewall Macro Definitions

*[Main Index](SKILL.md)*


Amanda

Action
PARAM
PARAM

Auth

Action
PARAM

BGP

Action
PARAM

BitTorrent

Action
PARAM
PARAM

BitTorrent32

Action
PARAM
PARAM

Amanda Backup

proto
udp
tcp

dport
10080
10080

sport

dport
113

sport

dport
179

sport

Auth (identd) traffic

proto
tcp

Border Gateway Protocol traffic

proto
tcp

BitTorrent traffic for BitTorrent 3.1 and earlier

proto
tcp
udp

dport
6881:6889
6881

sport

BitTorrent traffic for BitTorrent 3.2 and later

proto
tcp
udp

dport
6881:6999
6881

sport


CVS

Action
PARAM

Ceph

Action
PARAM
PARAM
PARAM

Citrix

Action
PARAM
PARAM
PARAM

DAAP

Action
PARAM
PARAM

DCC


Concurrent Versions System pserver traffic

proto
tcp

dport
2401

sport

Ceph Storage Cluster traffic (Ceph Monitors, OSD & MDS Daemons)

proto
tcp
tcp
tcp

dport
6789
3300
6800:7300

sport

Citrix/ICA traffic (ICA, ICA Browser, CGP)

proto
tcp
udp
tcp

dport
1494
1604
2598

sport

Digital Audio Access Protocol traffic (iTunes, Rythmbox daemons)

proto
tcp
udp

dport
3689
3689

sport

Distributed Checksum Clearinghouse spam filtering mechanism

Action
PARAM

proto
tcp

DHCPfwd

Forwarded DHCP traffic

Action
PARAM

proto
udp

DHCPv6

DHCPv6 traffic

dport
6277

sport

dport
67:68

sport
67:68

Action
PARAM

DNS

Action
PARAM
PARAM

Distcc

proto
udp

proto
udp
tcp

FTP

File Transfer Protocol

Action
PARAM

proto
tcp

GNUnet

Action
PARAM
PARAM
PARAM
PARAM

GRE

Action
PARAM

Git

sport
546:547

dport
53
53

sport

dport
3632

sport

dport
21

sport

dport
79

sport

Distributed Compiler service

proto
tcp

Action
PARAM

dport
546:547

Domain Name System traffic (upd and tcp)

Action
PARAM

Finger


Finger protocol (RFC 742)

proto
tcp

GNUnet secure peer-to-peer networking traffic

proto
tcp
udp
tcp
udp

dport
2086
2086
1080
1080

sport

Generic Routing Encapsulation tunneling protocol

proto
47

dport

Git distributed revision control traffic

sport

Action
PARAM

HKP

Action
PARAM

HTTP

Action
PARAM

HTTPS

Action
PARAM

ICPV2

Action
PARAM

ICQ

Action
PARAM

IMAP

Action
PARAM

IMAPS

Action
PARAM

proto
tcp


dport
9418

sport

OpenPGP HTTP key server protocol traffic

proto
tcp

dport
11371

sport

Hypertext Transfer Protocol (WWW)

proto
tcp

dport
80

sport

Hypertext Transfer Protocol (WWW) over SSL

proto
tcp

dport
443

sport

Internet Cache Protocol V2 (Squid) traffic

proto
udp

dport
3130

sport

dport
5190

sport

dport
143

sport

AOL Instant Messenger traffic

proto
tcp

Internet Message Access Protocol

proto
tcp

Internet Message Access Protocol over SSL

proto
tcp

dport
993

sport


IPIP

IPIP capsulation traffic

Action
PARAM

proto
94

IPsec

Action
PARAM
PARAM

IPsecah

Action
PARAM
PARAM

IPsecnat

Action
PARAM
PARAM
PARAM

IRC

dport

sport

dport
500

sport
500

dport
500

sport
500

dport
500
4500

sport

dport
6667

sport

dport
9100

sport

IPsec traffic

proto
udp
50

IPsec authentication (AH) traffic

proto
udp
51

IPsec traffic and Nat-Traversal

proto
udp
udp
50

Internet Relay Chat traffic

Action
PARAM

proto
tcp

Jetdirect

HP Jetdirect printing

Action
PARAM

proto
tcp

L2TP


Layer 2 Tunneling Protocol traffic

Action
PARAM

LDAP

Action
PARAM

LDAPS

proto
udp

proto
tcp

MDNS

Multicast DNS

Action
PARAM

proto
udp

proto
tcp

MSSQL

Microsoft SQL Server

Action
PARAM

proto
tcp

Munin

Action
PARAM

dport
389

sport

dport
636

sport

dport
5353

sport

dport
1863

sport

dport
1433

sport

Microsoft Notification Protocol

Action
PARAM

Action
PARAM
PARAM
PARAM

sport

Secure Lightweight Directory Access Protocol traffic

proto
tcp

Mail

dport
1701

Lightweight Directory Access Protocol traffic

Action
PARAM

MSNP


Mail traffic (SMTP, SMTPS, Submission)

proto
tcp
tcp
tcp

dport
25
465
587

sport

Munin networked resource monitoring traffic

proto
tcp

dport
4949

sport


MySQL

MySQL server

Action
PARAM

proto
tcp

NNTP

NNTP traffic (Usenet).

Action
PARAM

proto
tcp

NNTPS

Action
PARAM

NTP

Action
PARAM


dport
3306

sport

dport
119

sport

dport
563

sport

dport
123

sport

Encrypted NNTP traffic (Usenet)

proto
tcp

Network Time Protocol (ntpd)

proto
udp

NeighborDiscovery
IPv6 neighbor solicitation, neighbor and router advertisement

Action
PARAM
PARAM
PARAM
PARAM

proto
icmpv6
icmpv6
icmpv6
icmpv6

OSPF

OSPF multicast traffic

Action
PARAM

proto
89

OpenVPN

OpenVPN traffic

dport
router-solicitation
router-advertisement
neighbor-solicitation
neighboradvertisement

sport

dport

sport

Action
PARAM

PCA

Action
PARAM
PARAM

PMG

Action
PARAM

POP3

proto
udp

proto
udp
tcp

proto
tcp

Encrypted POP3 traffic

Action
PARAM

proto
tcp

Action
PARAM

PostgreSQL

Action
PARAM

dport
5632
5631

sport

dport
8006

sport

dport
110

sport

dport
995

sport

dport

sport

POP3 traffic

POP3S

Ping

sport

Proxmox Mail Gateway web interface

proto
tcp

Action
PARAM
PARAM

dport
1194

Symantec PCAnywere (tm)

Action
PARAM

PPtP


Point-to-Point Tunneling Protocol

proto
47
tcp

1723

ICMP echo request

proto
icmp

dport
echo-request

sport

dport
5432

sport

PostgreSQL server

proto
tcp


Printer

Action
PARAM

RDP

Action
PARAM

RIP

Action
PARAM

RNDC

Line Printer protocol printing

proto
tcp

dport
515

sport

Microsoft Remote Desktop Protocol traffic

proto
tcp

dport
3389

sport

Routing Information Protocol (bidirectional)

proto
udp

dport
520

sport

BIND remote management protocol

Action
PARAM

proto
tcp

Razor

Razor Antispam System

Action
PARAM

proto
tcp

Rdate


dport
953

sport

dport
2703

sport

dport
37

sport

dport
873

sport

Remote time retrieval (rdate)

Action
PARAM

proto
tcp

Rsync

Rsync server

Action
PARAM

proto
tcp


SANE

SANE network scanning

Action
PARAM

proto
tcp

SMB

Microsoft SMB traffic

Action
PARAM
PARAM
PARAM
PARAM

proto
udp
udp
udp
tcp

SMBswat

Action
PARAM

SMTP

Action
PARAM

SMTPS

Action
PARAM

SNMP

Action
PARAM
PARAM

SPAMD


dport
6566

sport

dport
135,445
137:139
1024:65535
135,139,445

sport

dport
901

sport

dport
25

sport

137

Samba Web Administration Tool

proto
tcp

Simple Mail Transfer Protocol

proto
tcp

Encrypted Simple Mail Transfer Protocol

proto
tcp

dport
465

sport

Simple Network Management Protocol

proto
udp
tcp

Spam Assassin SPAMD traffic

dport
161:162
161

sport

Action
PARAM

SPICEproxy

Action
PARAM

SSH

Action
PARAM

SVN

Action
PARAM

SixXS

proto
tcp

proto
tcp

proto
tcp

dport
3128

sport

dport
22

sport

dport
3690

sport

Subversion server (svnserve)

proto
tcp

SixXS IPv6 Deployment and Tunnel Broker

Squid

Squid web proxy traffic

Action
PARAM

proto
tcp

Syslog

sport

Secure shell traffic

proto
tcp
udp
41
udp

Action
PARAM

dport
783

Proxmox VE SPICE display proxy traffic

Action
PARAM
PARAM
PARAM
PARAM

Submission


dport
3874
3740

sport

5072,8374

dport
3128

sport

dport
587

sport

Mail message submission traffic

proto
tcp

Syslog protocol (RFC 5424) traffic

Action
PARAM
PARAM

TFTP

Action
PARAM

Telnet

proto
udp
tcp

proto
udp

Telnets

Telnet over SSL

Action
PARAM

proto
tcp

Time

RFC 868 Time protocol

Action
PARAM

proto
tcp

VNC

Action
PARAM

VNCL

Action
PARAM

sport

dport
69

sport

dport
23

sport

dport
992

sport

dport
37

sport

Telnet traffic

proto
tcp

Action
PARAM
PARAM

dport
514
514

Trivial File Transfer Protocol traffic

Action
PARAM

Trcrt


Traceroute (for up to 30 hops) traffic

proto
udp
icmp

dport
33434:33524
echo-request

sport

VNC traffic for VNC display’s 0 - 99

proto
tcp

dport
5900:5999

sport

VNC traffic from Vncservers to Vncviewers in listen mode

proto
tcp

dport
5500

sport


Web

Action
PARAM
PARAM

Webcache

WWW traffic (HTTP and HTTPS)

proto
tcp
tcp

proto
tcp

Webmin

Webmin traffic

Action
PARAM

proto
tcp

Action
PARAM

dport
80
443

sport

Web Cache/Proxy traffic (port 8080)

Action
PARAM

Whois


dport
8080

sport

dport
10000

sport

dport
43

sport

Whois (nicname, RFC 3912) traffic

proto
tcp

## See also

- [Firewall](ch13-firewall/_index.md)

