# skill-writer checklist - compuse-ssh (2026-11-16, looking up a key in a hashed known_hosts)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` printed nothing; the one live
      rule (d-20261115-96797719, Windows sshd) is untouched.
- [x] Premise checked: the old text covered recording (`accept-new`) and removing (`-R`) keys and
      had no lookup method and no mention of hashing. The claim was re-measured, not inherited:
      a scratch known_hosts with a dummy ed25519 key for `example.test` and `192.0.2.10`, hashed
      with `ssh-keygen -H` (OpenSSH 10.2p1): `grep -c` for either printed 0; `ssh-keygen -F`
      found both (exit 0); an absent name exited 1 with no output; a missing file exited 255
      (`Cannot stat`); `[example.test]:2222` was found only in bracket form, not as the bare name;
      a plaintext line appended to the hashed file was the only `grep` hit.
- [x] Default checked, not assumed: Ubuntu 26.04's `/etc/ssh/ssh_config` sets
      `HashKnownHosts yes` under `Host *` (package openssh-client); ssh_config(5) gives `no` as
      the OpenSSH default for both `HashKnownHosts` and `CheckHostIP`. Debian is stated from the
      same Debian-packaged file; not re-measured on a Debian box.
- [x] `ssh -F <cfg> -G` with a `Host 192.0.2.*` block: the address printed the fleet file, a host
      name printed the default `known_hosts known_hosts2` (two files, hence "check each").
- [x] RED (pre-edit excerpt, opus and haiku `baseline-probe`): both quoted NONE for a lookup
      method and reached `ssh-keygen -F` from their own knowledge only. Gaps they named: no lookup
      method, no mention of hashing, `Host` matching the typed name, which name is recorded.
- [x] GREEN (new paragraph, opus and haiku quote-back): both said "not determined" instead of
      "absent", ran `ssh-keygen -F` for name and address, read exit 0/1 correctly and used
      `'[web3]:2222'` for the non-22 port, each from quoted lines.
- [x] GREEN gaps closed: a missing file's exit code (255, measured), a split verdict between name
      and address ("count a find under either as recorded"), and the wrong-file case (`Host`
      matches the typed name; `ssh -G` lists the files). Re-probe on the final paragraph, haiku:
      all four touched questions answered from quotes.
- [x] Gaps declined: what to do when the file is missing (outside a lookup's scope; the existing
      text says how the file is set up); grep false positives on substrings (the rule is "never
      grep", so a grep hit is not the method); which canonical name ssh records under
      `CanonicalizeHostname` (an opt-in setting, not the default path).
- [x] Width and fence check over the added lines printed nothing; ASCII only; example values are
      reserved (`192.0.2.*`, `host.example`); description unchanged.
- [x] Decisions: d-20261116-ee6bcfb3
