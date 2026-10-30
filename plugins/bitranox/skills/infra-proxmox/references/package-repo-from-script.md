# Reading the PVE package repository from a script

`apt` is the normal client. When a script needs the index itself (which versions exist, the hash
of a given `.deb`), fetch it the way `apt` does and check the signature yourself. Verified against
the Debian 13 (trixie) repository.

## Use http, not https, on download.proxmox.com

`https://download.proxmox.com` fails certificate verification: the host serves a certificate for
`enterprise.proxmox.com` and the `*.cdn.proxmox.com` names, not for `download.proxmox.com`
(`curl` exits 60, Python raises `CERTIFICATE_VERIFY_FAILED`). The no-subscription and test suites
are not on `enterprise.proxmox.com` either: everything there answers `401` without a subscription.
`apt` itself fetches over http and trusts the signature, so do the same:

```text
http://download.proxmox.com/debian/pve/dists/trixie/InRelease
```

## Trust comes from the signature

1. Get the release key from `https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg`
   (the same file a PVE 9 node holds as `/usr/share/keyrings/proxmox-release-trixie.gpg`) and check
   its fingerprint: `gpg --show-keys --with-colons <file> | grep ^fpr` must print
   `24B30F06ECC1836A4E5EFECBA7BCD1420BFE778E`.
2. `gpgv --keyring <keyfile> --output <signed.txt> InRelease`, and REQUIRE exit 0. `gpgv` writes
   `--output` even when the signature does not verify (exit 2), so a script that only reads the
   file accepts an unsigned index.
3. Parse ONLY `signed.txt`, never `InRelease` itself: `gpgv` accepts and drops text placed before
   the signed block, so anything parsed outside its output is unauthenticated.
4. The `SHA256:` list in `signed.txt` gives the hash of each component's `Packages.gz`. Check the
   download against it, then take each package's `SHA256` from `Packages`. A `.deb` lives at
   `http://download.proxmox.com/debian/pve/` plus its `Filename` field.

## Components

The signed `Components:` line reads `pve-no-subscription pve-test`. Use `pve-test`: an old
`pvetest` directory still answers `200`, but no signed index covers it. Old package versions stay
listed in `Packages`, so the hash of a specific older version can be checked offline.
