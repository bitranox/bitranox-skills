# Users, Groups, Tokens, and Pools

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Proxmox VE supports multiple authentication sources, for example Linux PAM, an integrated Proxmox VE
authentication server, LDAP, Microsoft Active Directory and OpenID Connect.
By using role-based user and permission management for all objects (VMs, Storage, nodes, etc.), granular
access can be defined.


## 14.1 Users


Proxmox VE stores user attributes in /etc/pve/user.cfg. Passwords are not stored here; users are
instead associated with the authentication realms described below. Therefore, a user is often internally
identified by their username and realm in the form <userid>@<realm>.
Each user entry in this file contains the following information:

- First name
- Last name
- E-mail address
- Group memberships
- An optional expiration date
- A comment or note about this user
- Whether this user is enabled or disabled
- Optional two-factor authentication keys

> **Caution:**
> When you disable or delete a user, or if the expiry date set is in the past, this user will not be able
> to log in to new sessions or start new tasks. All tasks which have already been started by this user
> (for example, terminal sessions) will not be terminated automatically by any such event.


### 14.1.1 System administrator


The system’s root user can always log in via the Linux PAM realm and is an unconfined administrator. This
user cannot be deleted, but attributes can still be changed. System mails will be sent to the email address
assigned to this user.


## 14.2 Groups


Each user can be a member of several groups. Groups are the preferred way to organize access permissions. You should always grant permissions to groups instead of individual users. That way you will get a
much more maintainable access control list.


## 14.3 API Tokens


API tokens allow stateless access to most parts of the REST API from another system, software or API
client. Tokens can be generated for individual users and can be given separate permissions and expiration
dates to limit the scope and duration of the access. Should the API token get compromised, it can be revoked
without disabling the user itself.
API tokens come in two basic types:

- Separated privileges: The token needs to be given explicit access with ACLs. Its effective permissions are
calculated by intersecting user and token permissions.

- Full privileges: The token’s permissions are identical to that of the associated user.

> **Caution:**
> The token value is only displayed/returned once when the token is generated. It cannot be retrieved
> again over the API at a later time!


To use an API token, set the HTTP header Authorization to the displayed value of the form PVEAPIToken=USER@
when making API requests, or refer to your API client’s documentation.


## 14.4 Resource Pools


A resource pool is a set of virtual machines, containers, and storage devices. It is useful for permission
handling in cases where certain users should have controlled access to a specific set of resources, as it
allows for a single permission to be applied to a set of elements, rather than having to manage this on a
per-resource basis. Resource pools are often used in tandem with groups, so that the members of a group
have permissions on a set of machines and storage.


## 14.5 Authentication Realms


As Proxmox VE users are just counterparts for users existing on some external realm, the realms have to be
configured in /etc/pve/domains.cfg. The following realms (authentication methods) are available:

Linux PAM Standard Authentication
Linux PAM is a framework for system-wide user authentication. These users are created on the host
system with commands such as adduser. If PAM users exist on the Proxmox VE host system,
corresponding entries can be added to Proxmox VE, to allow these users to log in via their system
username and password.
Proxmox VE Authentication Server
This is a Unix-like password store, which stores hashed passwords in /etc/pve/priv/shadow.cfg.
Passwords are hashed using the SHA-256 hashing algorithm. This is the most convenient realm for
small-scale (or even mid-scale) installations, where users do not need access to anything outside of
Proxmox VE. In this case, users are fully managed by Proxmox VE and are able to change their own
passwords via the GUI.
LDAP
LDAP (Lightweight Directory Access Protocol) is an open, cross-platform protocol for authentication
using directory services. OpenLDAP is a popular open-source implementations of the LDAP protocol.
Microsoft Active Directory (AD)
Microsoft Active Directory (AD) is a directory service for Windows domain networks and is supported
as an authentication realm for Proxmox VE. It supports LDAP as an authentication protocol.
OpenID Connect
OpenID Connect is implemented as an identity layer on top of the OAuth 2.0 protocol. It allows clients
to verify the identity of the user, based on authentication performed by an external authorization server.


### 14.5.1 Linux PAM Standard Authentication


As Linux PAM corresponds to host system users, a system user must exist on each node which the user
is allowed to log in on. The user authenticates with their usual system password. This realm is added by
default and can’t be removed.
Password changes via the GUI or, equivalently, the /access/password API endpoint only apply to
the local node and not cluster-wide. Even though Proxmox VE has a multi-master design, using different
passwords for different nodes can still offer a security benefit.
In terms of configurability, an administrator can choose to require two-factor authentication with logins from
the realm and to set the realm as the default authentication realm.


### 14.5.2 Proxmox VE Authentication Server


The Proxmox VE authentication server realm is a simple Unix-like password store. The realm is created by
default, and as with Linux PAM, the only configuration items available are the ability to require two-factor
authentication for users of the realm, and to set it as the default realm for login.


Unlike the other Proxmox VE realm types, users are created and authenticated entirely through Proxmox VE,
rather than authenticating against another system. Hence, you are required to set a password for this type
of user upon creation.


### 14.5.3 LDAP


You can also use an external LDAP server for user authentication (for example, OpenLDAP). In this realm
type, users are searched under a Base Domain Name (base_dn), using the username attribute specified
in the User Attribute Name (user_attr) field.
A server and optional fallback server can be configured, and the connection can be encrypted via SSL.
Furthermore, filters can be configured for directories and groups. Filters allow you to further limit the scope
of the realm.
For instance, if a user is represented via the following LDIF dataset:

# user1 of People at ldap-test.com
dn: uid=user1,ou=People,dc=ldap-test,dc=com
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
uid: user1
cn: Test User 1
sn: Testers
description: This is the first test user.
The Base Domain Name would be ou=People,dc=ldap-test,dc=com and the user attribute would
be uid.

If Proxmox VE needs to authenticate (bind) to the LDAP server before being able to query and authenticate
users, a bind domain name can be configured via the bind_dn property in /etc/pve/domains.cfg.
Its password then has to be stored in /etc/pve/priv/realm/<realmname>.pw (for example, /etc/pve
This file should contain a single line with the raw password.
To verify certificates, you need to set capath. You can set it either directly to the CA certificate of your LDAP
server, or to the system path containing all trusted CA certificates (/etc/ssl/certs). Additionally, you
need to set the verify option, which can also be done over the web interface.
The main configuration options for an LDAP server realm are as follows:

- Realm (realm): The realm identifier for Proxmox VE users
- Base Domain Name (base_dn): The directory which users are searched under
- User Attribute Name (user_attr): The LDAP attribute containing the username that users will
log in with

- Server (server1): The server hosting the LDAP directory
- Fallback Server (server2): An optional fallback server address, in case the primary server is
unreachable

- Port (port): The port that the LDAP server listens on


> **Note:**
> In order to allow a particular user to authenticate using the LDAP server, you must also add them as a
> user of that realm from the Proxmox VE server. This can be carried out automatically with syncing.


### 14.5.4 Microsoft Active Directory (AD)


To set up Microsoft AD as a realm, a server address and authentication domain need to be specified. Active
Directory supports most of the same properties as LDAP, such as an optional fallback server, port, and
SSL encryption. Furthermore, users can be added to Proxmox VE automatically via sync operations, after
configuration.
As with LDAP, if Proxmox VE needs to authenticate before it binds to the AD server, you must configure the
Bind User (bind_dn) property. This property is typically required by default for Microsoft AD.
The main configuration settings for Microsoft Active Directory are:

- Realm (realm): The realm identifier for Proxmox VE users
- Domain (domain): The AD domain of the server
- Server (server1): The FQDN or IP address of the server
- Fallback Server (server2): An optional fallback server address, in case the primary server is
unreachable

- Port (port): The port that the Microsoft AD server listens on

> **Note:**
> Microsoft AD normally checks values like usernames without case sensitivity. To make Proxmox VE do the
> same, you can disable the default case-sensitive option by editing the realm in the web UI, or using
> the CLI (change the ID with the realm ID): pveum realm modify ID --case-sensitive 0


### 14.5.5 Syncing LDAP-Based Realms


It’s possible to automatically sync users and groups for LDAP-based realms (LDAP & Microsoft Active Directory), rather than having to add them to Proxmox VE manually. You can access the sync options from the Add/Edit window of the web interface’s Authentication panel or via the pveum realm add/modify
