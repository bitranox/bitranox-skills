# Authentication Realms

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


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


commands. You can then carry out the sync operation from the Authentication panel of the GUI or
using the following command:


```
pveum realm sync <realm>
```

Users and groups are synced to the cluster-wide configuration file, /etc/pve/user.cfg.

Attributes to Properties
If the sync response includes user attributes, they will be synced into the matching user property in the
user.cfg. For example: firstname or lastname.
If the names of the attributes are not matching the Proxmox VE properties, you can set a custom field-to-field
map in the config by using the sync_attributes option.
How such properties are handled if anything vanishes can be controlled via the sync options, see below.

Sync Configuration
The configuration options for syncing LDAP-based realms can be found in the Sync Options tab of the
Add/Edit window.
The configuration options are as follows:

- Bind User (bind_dn): Refers to the LDAP account used to query users and groups. This account
needs access to all desired entries. If it’s set, the search will be carried out via binding; otherwise, the
search will be carried out anonymously. The user must be a complete LDAP formatted distinguished name
(DN), for example, cn=admin,dc=example,dc=com.

- Groupname attr. (group_name_attr): Represents the users’ groups. Only entries which adhere to the
usual character limitations of the user.cfg are synced. Groups are synced with -$realm attached
to the name, in order to avoid naming conflicts. Please ensure that a sync does not overwrite manually
created groups.

- User classes (user_classes): Objects classes associated with users.
- Group classes (group_classes): Objects classes associated with groups.
- E-Mail attribute: If the LDAP-based server specifies user email addresses, these can also be
included in the sync by setting the associated attribute here. From the command line, this is achievable
through the --sync_attributes parameter.

- User Filter (filter): For further filter options to target specific users.
- Group Filter (group_filter): For further filter options to target specific groups.

> **Note:**
> Filters allow you to create a set of additional match criteria, to narrow down the scope of a sync. Information on available LDAP filter types and their usage can be found at ldap.com.


Sync Options

In addition to the options specified in the previous section, you can also configure further options that describe the behavior of the sync operation.

These options are either set as parameters before the sync, or as defaults via the realm option sync-defaultsThe main options for syncing are:

- Scope (scope): The scope of what to sync. It can be either users, groups or both.
- Enable new (enable-new): If set, the newly synced users are enabled and can log in. The default is
true.
- Remove Vanished (remove-vanished): This is a list of options which, when activated, determine
if they are removed when they are not returned from the sync response. The options are:

– ACL (acl): Remove ACLs of users and groups which were not returned returned in the sync response.
This most often makes sense together with Entry.
– Entry (entry): Removes entries (i.e. users and groups) when they are not returned in the sync
response.

– Properties (properties): Removes properties of entries where the user in the sync response
did not contain those attributes. This includes all properties, even those never set by a sync. Exceptions
are tokens and the enable flag, these will be retained even with this option enabled.

- Preview (dry-run): No data is written to the config. This is useful if you want to see which users and
groups would get synced to the user.cfg.
Reserved characters
Certain characters are reserved (see RFC2253) and cannot be easily used in attribute values in DNs without
being escaped properly.
Following characters need escaping:

- Space ( ) at the beginning or end
- Number sign (#) at the beginning
- Comma (,)


- Plus sign (+)
- Double quote (")
- Forward slashes (/)
- Angle brackets (<>)
- Semicolon (;)
- Equals sign (=)

To use such characters in DNs, surround the attribute value in double quotes. For example, to bind with a user
with the CN (Common Name) Example, User, use CN="Example, User",OU=people,DC=example,
as value for bind_dn.
This applies to the base_dn, bind_dn, and group_dn attributes.

> **Note:**
> Users with colons and forward slashes cannot be synced since these are reserved characters in usernames.


### 14.5.6 OpenID Connect


The main OpenID Connect configuration options are:

- Issuer URL (issuer-url): This is the URL of the authorization server. Proxmox VE uses the
OpenID Connect Discovery protocol to automatically configure further details.
While it is possible to use unencrypted http:// URLs, we strongly recommend to use encrypted
https:// connections.

- Realm (realm): The realm identifier for Proxmox VE users
- Client ID (client-id): OpenID Client ID.
- Client Key (client-key): Optional OpenID Client Key.
- Autocreate Users (autocreate): Automatically create users if they do not exist. While authentication is done at the OpenID server, all users still need an entry in the Proxmox VE user configuration.
You can either add them manually, or use the autocreate option to automatically add new users.

- Username Claim (username-claim): OpenID claim used to generate the unique username (subject,
username or email).
- Autocreate Groups (groups-autocreate): Create all groups in the claim instead of using existing PVE groups (default behavior).

- Groups Claim (groups-claim): OpenID claim used to retrieve the groups from the ID token or
userinfo endpoint.

- Overwrite Groups (groups-overwrite): Overwrite all groups assigned to user instead of appending to existing groups (default behavior).


Username mapping
The OpenID Connect specification defines a single unique attribute (claim in OpenID terms) named subject.
By default, we use the value of this attribute to generate Proxmox VE usernames, by simple adding @ and
the realm name: ${subject}@${realm}.
Unfortunately, most OpenID servers use random strings for subject, like DGH76OKH34BNG3245SB, so
a typical username would look like DGH76OKH34BNG3245SB@yourrealm. While unique, it is difficult
for humans to remember such random strings, making it quite impossible to associate real users with this.
The username-claim setting allows you to use other attributes for the username mapping. Setting it to
username is preferred if the OpenID Connect server provides that attribute and guarantees its uniqueness.
Another option is to use email, which also yields human readable usernames. Again, only use this setting
if the server guarantees the uniqueness of this attribute.

Groups mapping
Specifying the groups-claim setting in the OpenID configuration enables group mapping functionality.
The data provided in the groups-claim should be a list of strings that correspond to groups that a
user should be a member of in Proxmox VE. To prevent collisions, group names from the OpenID claim
are suffixed with -<realm name> (e.g. for the OpenID group name my-openid-group in the realm
oidc, the group name in Proxmox VE would be my-openid-group-oidc).
Any groups reported by the OpenID provider that do not exist in Proxmox VE are ignored by default. If all
groups reported by the OpenID provider should exist in Proxmox VE, the groups-autocreate option
may be used to automatically create these groups on user logins.
By default, groups are appended to the user’s existing groups. It may be desirable to overwrite any groups
that the user is already a member in Proxmox VE with those from the OpenID provider. Enabling the
groups-overwrite setting removes all groups from the user in Proxmox VE before adding the groups
reported by the OpenID provider.
In some cases, OpenID servers may send groups claims which include invalid characters for Proxmox VE
group IDs. Any groups that contain characters not allowed in a Proxmox VE group name are not included
and a warning will be sent to the logs.

Advanced settings

- Query userinfo endpoint (query-userinfo): Enabling this option requires the OpenID Connect authenticator to query the "userinfo" endpoint for claim values. Disabling this option is useful for some
identity providers that do not support the "userinfo" endpoint (e.g. ADFS).

Examples
Here is an example of creating an OpenID realm using Google. You need to replace --client-id and
- `--client-key` with the values from your Google OpenID settings.


```
pveum realm add myrealm1 --type openid --issuer-url https://accounts. ←google.com --client-id XXXX --client-key YYYY --username-claim email
```


The above command uses --username-claim email, so that the usernames on the Proxmox VE
side look like example.user@google.com@myrealm1.

Keycloak (https://www.keycloak.org/) is a popular open source Identity and Access Management tool, which
supports OpenID Connect. In the following example, you need to replace the --issuer-url and --client-i
with your information:


```
pveum realm add myrealm2 --type openid --issuer-url https://your.server ←:8080/realms/your-realm --client-id XXX --username-claim username
```


Using --username-claim username enables simple usernames on the Proxmox VE side, like example.u


> **Warning:**
> You need to ensure that the user is not allowed to edit the username setting themselves (on the
> Keycloak server).


## 14.6 Two-Factor Authentication


There are two ways to use two-factor authentication:
It can be required by the authentication realm, either via TOTP (Time-based One-Time Password) or YubiKey
OTP. In this case, a newly created user needs to have their keys added immediately, as there is no way to
log in without the second factor. In the case of TOTP, users can also change the TOTP later on, provided
they can log in first.
Alternatively, users can choose to opt-in to two-factor authentication later on, even if the realm does not
enforce it.


### 14.6.1 Available Second Factors


You can set up multiple second factors, in order to avoid a situation in which losing your smartphone or
security key locks you out of your account permanently.
The following two-factor authentication methods are available in addition to realm-enforced TOTP and YubiKey OTP:

- User configured TOTP (Time-based One-Time Password). A short code derived from a shared secret and
the current time, it changes every 30 seconds.

- WebAuthn (Web Authentication). A general standard for authentication. It is implemented by various
security devices, like hardware keys or trusted platform modules (TPM) from a computer or smart phone.

- Single use Recovery Keys. A list of keys which should either be printed out and locked in a secure place
or saved digitally in an electronic vault. Each key can be used only once. These are perfect for ensuring
that you are not locked out, even if all of your other second factors are lost or corrupt.
Before WebAuthn was supported, U2F could be setup by the user. Existing U2F factors can still be used,
but it is recommended to switch to WebAuthn, once it is configured on the server.


### 14.6.2 Realm Enforced Two-Factor Authentication


This can be done by selecting one of the available methods via the TFA dropdown box when adding or editing
an Authentication Realm. When a realm has TFA enabled, it becomes a requirement, and only users with
configured TFA will be able to log in.
Currently there are two methods available:

Time-based OATH (TOTP)
This uses the standard HMAC-SHA1 algorithm, where the current time is hashed with the user’s
configured key. The time step and password length parameters are configurable.
A user can have multiple keys configured (separated by spaces), and the keys can be specified in
Base32 (RFC3548) or hexadecimal notation.
Proxmox VE provides a key generation tool (oathkeygen) which prints out a random key in Base32
notation, that can be used directly with various OTP tools, such as the oathtool command-line tool,
or on Android Google Authenticator, FreeOTP, andOTP or similar applications.
YubiKey OTP
For authenticating via a YubiKey a Yubico API ID, API KEY and validation server URL must be configured, and users must have a YubiKey available. In order to get the key ID from a YubiKey, you can
trigger the YubiKey once after connecting it via USB, and copy the first 12 characters of the typed
password into the user’s Key IDs field.
Please refer to the YubiKey OTP documentation for how to use the YubiCloud or host your own verification
server.


### 14.6.3 Limits and Lockout of Two-Factor Authentication


A second factor is meant to protect users if their password is somehow leaked or guessed. However, some
factors could still be broken by brute force. For this reason, users will be locked out after too many failed 2nd
factor login attempts.
For TOTP, 8 failed attempts will disable the user’s TOTP factors. They are unlocked when logging in with a
recovery key. If TOTP was the only available factor, admin intervention is required, and it is highly recommended to require the user to change their password immediately.
Since FIDO2/Webauthn and recovery keys are less susceptible to brute force attacks, the limit there is higher
(100 tries), but all second factors are blocked for an hour when exceeded.
An admin can unlock a user’s Two-Factor Authentication at any time via the user list in the UI or the command
line:


```
pveum user tfa unlock joe@pve
```


### 14.6.4 User Configured TOTP Authentication


Users can choose to enable TOTP or WebAuthn as a second factor on login, via the TFA button in the user
list (unless the realm enforces YubiKey OTP).


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
