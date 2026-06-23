# User Management

*[Main Index](../SKILL.md)*

## Contents

| Section                                      | File                                                       |
|----------------------------------------------|------------------------------------------------------------|
| 14.1-14.4 Users, Groups, Tokens, and Pools   | [users-groups-tokens.md](users-groups-tokens.md)           |
| 14.5 Authentication Realms                   | [authentication-realms.md](authentication-realms.md)       |
| 14.6 Two-Factor Authentication               | [two-factor-auth.md](two-factor-auth.md)                   |
| 14.7-14.9 Permission Management and Examples | [permissions-and-examples.md](permissions-and-examples.md) |


## See also

- [Firewall](../ch13-firewall/_index.md)
- [pveum CLI Reference](../appendix-a-cli/pveum.md)

## Overview

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
