# Two-Factor Authentication

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Users can always add and use one time Recovery Keys.

After opening the TFA window, the user is presented with a dialog to set up TOTP authentication. The Secret
field contains the key, which can be randomly generated via the Randomize button. An optional Issuer Name
can be added to provide information to the TOTP app about what the key belongs to. Most TOTP apps will
show the issuer name together with the corresponding OTP values. The username is also included in the
QR code for the TOTP app.
After generating a key, a QR code will be displayed, which can be used with most OTP apps such as FreeOTP.
The user then needs to verify the current user password (unless logged in as root), as well as the ability to
correctly use the TOTP key, by typing the current OTP value into the Verification Code field and pressing the
Apply button.


### 14.6.5 TOTP


There is no server setup required. Simply install a TOTP app on your smartphone (for example, FreeOTP)
and use the Proxmox VE web interface to add a TOTP factor.


### 14.6.6 WebAuthn


For WebAuthn to work, you need to have two things:

- A trusted HTTPS certificate (for example, by using Let’s Encrypt). While it probably works with an untrusted
certificate, some browsers may warn or refuse WebAuthn operations if it is not trusted.

- Setup the WebAuthn configuration (see Datacenter → Options → WebAuthn Settings in the Proxmox
VE web interface). This can be auto-filled in most setups.
Once you have fulfilled both of these requirements, you can add a WebAuthn configuration in the Two Factor
panel under Datacenter → Permissions → Two Factor.


### 14.6.7 Recovery Keys


Recovery key codes do not need any preparation; you can simply create a set of recovery keys in the Two
Factor panel under Datacenter → Permissions → Two Factor.


> **Note:**
> There can only be one set of single-use recovery keys per user at any time.


### 14.6.8 Server Side Webauthn Configuration


To allow users to use WebAuthn authentication, it is necessary to use a valid domain with a valid SSL
certificate, otherwise some browsers may warn or refuse to authenticate altogether.

> **Note:**
> Changing the WebAuthn configuration may render all existing WebAuthn registrations unusable!


This is done via /etc/pve/datacenter.cfg. For instance:

webauthn: rp=mypve.example.com,origin=https://mypve.example.com:8006,id= ←mypve.example.com


### 14.6.9 Server Side U2F Configuration


> **Note:**
> It is recommended to use WebAuthn instead.


To allow users to use U2F authentication, it may be necessary to use a valid domain with a valid SSL
certificate, otherwise, some browsers may print a warning or reject U2F usage altogether. Initially, an AppId
1 needs to be configured.

> **Note:**
> Changing the AppId will render all existing U2F registrations unusable!


This is done via /etc/pve/datacenter.cfg. For instance:

u2f: appid=https://mypve.example.com:8006
1 AppId https://developers.yubico.com/U2F/App_ID.html


For a single node, the AppId can simply be the address of the web interface, exactly as it is used in the
browser, including the https:// and the port, as shown above. Please note that some browsers may be more
strict than others when matching AppIds.
When using multiple nodes, it is best to have a separate https server providing an appid.json 2 file,
as it seems to be compatible with most browsers. If all nodes use subdomains of the same top level domain,
it may be enough to use the TLD as AppId. It should however be noted that some browsers may not accept
this.

> **Note:**
> A bad AppId will usually produce an error, but we have encountered situations when this does not happen,
> particularly when using a top level domain AppId for a node that is accessed via a subdomain in Chromium.
> For this reason it is recommended to test the configuration with multiple browsers, as changing the AppId
> later will render existing U2F registrations unusable.


### 14.6.10 Activating U2F as a User


To enable U2F authentication, open the TFA window’s U2F tab, type in the current password (unless logged
in as root), and press the Register button. If the server is set up correctly and the browser accepts the
server’s provided AppId, a message will appear prompting the user to press the button on the U2F device (if
it is a YubiKey, the button light should be toggling on and off steadily, roughly twice per second).
Firefox users may need to enable security.webauth.u2f via about:config before they can use a U2F token.


## 14.7 Permission Management


In order for a user to perform an action (such as listing, modifying or deleting parts of a VM’s configuration),
the user needs to have the appropriate permissions.
Proxmox VE uses a role and path based permission management system. An entry in the permissions table
allows a user, group or token to take on a specific role when accessing an object or path. This means that
such an access rule can be represented as a triple of (path, user, role), (path, group, role) or (path, token,
role), with the role containing a set of allowed actions, and the path representing the target of these actions.


### 14.7.1 Roles


A role is simply a list of privileges. Proxmox VE comes with a number of predefined roles, which satisfy most
requirements.

- Administrator: has full privileges
- NoAccess: has no privileges (used to forbid access)

- PVEAdmin: can do most tasks, but has no rights to modify system settings (Sys.PowerMgmt, Sys.Modify,
Realm.Allocate) or permissions (Permissions.Modify)
- PVEAuditor: has read only access
2 Multi-facet apps: https://developers.yubico.com/U2F/App_ID.html


- PVEDatastoreAdmin: create and allocate backup space and templates
- PVEDatastoreUser: allocate backup space and view storage
- PVEMappingAdmin: manage resource mappings
- PVEMappingUser: view and use resource mappings
- PVEPoolAdmin: allocate pools
- PVEPoolUser: view pools
- PVESDNAdmin: manage SDN configuration
- PVESDNUser: access to bridges/vnets
- PVESysAdmin: audit, system console and system logs
- PVETemplateUser: view and clone templates
- PVEUserAdmin: manage users
- PVEVMAdmin: fully administer VMs
- PVEVMUser: view, backup, configure CD-ROM, VM console, VM power management
You can see the whole set of predefined roles in the GUI.
You can add new roles via the GUI or the command line.

From the GUI, navigate to the Permissions → Roles tab from Datacenter and click on the Create button.
There you can set a role name and select any desired privileges from the Privileges drop-down menu.
To add a role through the command line, you can use the pveum CLI tool, for example:


```
pveum role add VM_Power-only --privs "VM.PowerMgmt VM.Console"
```


```
pveum role add Sys_Power-only --privs "Sys.PowerMgmt Sys.Console"
```


> **Note:**
> Roles starting with PVE are always builtin, custom roles are not allowed use this reserved prefix.


### 14.7.2 Privileges


A privilege is the right to perform a specific action. To simplify management, lists of privileges are grouped
into roles, which can then be used in the permission table. Note that privileges cannot be directly assigned
to users and paths without being part of a role.
We currently support the following privileges:


Node / System related privileges

- Group.Allocate: create/modify/remove groups
- Mapping.Audit: view resource mappings
- Mapping.Modify: manage resource mappings
- Mapping.Use: use resource mappings
- Permissions.Modify: modify access permissions
- Pool.Allocate: create/modify/remove a pool
- Pool.Audit: view a pool
- Realm.AllocateUser: assign user to a realm
- Realm.Allocate: create/modify/remove authentication realms
- SDN.Allocate: manage SDN configuration
- SDN.Audit: view SDN configuration
- Sys.Audit: view node status/config, Corosync cluster config, and HA config
- Sys.Console: console access to node
- Sys.Incoming: allow incoming data streams from other clusters (experimental)
- Sys.Modify: create/modify/remove node network parameters
- Sys.PowerMgmt: node power management (start, stop, reset, shutdown, . . . )
- Sys.Syslog: view syslog
- User.Modify: create/modify/remove user access and details.
Virtual machine related privileges

- SDN.Use: access SDN vnets and local network bridges
- VM.Allocate: create/remove VM on a server
- VM.Audit: view VM config
- VM.Backup: backup/restore VMs
- VM.Clone: clone/copy a VM
- VM.Config.CDROM: eject/change CD-ROM
- VM.Config.CPU: modify CPU settings
- VM.Config.Cloudinit: modify Cloud-init parameters
- VM.Config.Disk: add/modify/remove disks
- VM.Config.HWType: modify emulated hardware types
- VM.Config.Memory: modify memory settings
- VM.Config.Network: add/modify/remove network devices
- VM.Config.Options: modify any other VM configuration
- VM.Console: console access to VM
- VM.GuestAgent.Audit: issue informational QEMU guest agent commands
- VM.GuestAgent.FileRead: read files from the guest via QEMU guest agent


- VM.GuestAgent.FileSystemMgmt: freeze/thaw/trim file systems via QEMU guest agent
- VM.GuestAgent.FileWrite: write files in the guest via QEMU guest agent
- VM.GuestAgent.Unrestricted: issue arbitrary QEMU guest agent commands
- VM.Migrate: migrate VM to alternate server on cluster
- VM.PowerMgmt: power management (start, stop, reset, shutdown, . . . )
- VM.Replicate: configure and run guest replication
- VM.Snapshot.Rollback: rollback VM to one of its snapshots
- VM.Snapshot: create/delete VM snapshots
Storage related privileges

- Datastore.Allocate: create/modify/remove a datastore and delete volumes
- Datastore.AllocateSpace: allocate space on a datastore
- Datastore.AllocateTemplate: allocate/upload templates and ISO images
- Datastore.Audit: view/browse a datastore

> **Warning:**
> Both Permissions.Modify and Sys.Modify should be handled with care, as they allow
> modifying aspects of the system and its configuration that are dangerous or sensitive.


> **Warning:**
> Carefully read the section about inheritance below to understand how assigned roles (and their
> privileges) are propagated along the ACL tree.


### 14.7.3 Objects and Paths


Access permissions are assigned to objects, such as virtual machines, storages or resource pools. We use
file system like paths to address these objects. These paths form a natural tree, and permissions of higher
levels (shorter paths) can optionally be propagated down within this hierarchy.
Paths can be templated. When an API call requires permissions on a templated path, the path may contain
references to parameters of the API call. These references are specified in curly braces. Some parameters
are implicitly taken from the API call’s URI. For instance, the permission path /nodes/{node} when
calling /nodes/mynode/status requires permissions on /nodes/mynode, while the path {path} in a
PUT request to /access/acl refers to the method’s path parameter.
Some examples are:

- /nodes/{node}: Access to Proxmox VE server machines
- /vms: Covers all VMs
- /vms/{vmid}: Access to specific VMs
