# skill-writer checklist - compuse-ssh (2026-08-02, stop recommending /dev/null; require BatchMode)

Change: the trusted-subnet guidance no longer recommends `UserKnownHostsFile=/dev/null`, the
key-auth row now requires `BatchMode=yes -o PreferredAuthentications=publickey`, and two rows are
added (pick a shared key by READABILITY; scp carries the user inside the path).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued this session).
- [x] The skill CAUSED a bug it separately documented. It recommended `/dev/null` in a table row and
      in its `~/.ssh/config` block, then a later row described the `Warning: Permanently added ...`
      line splicing into file content - without ever connecting the two. `/dev/null` is exactly what
      makes that line repeat on every call, because ssh records the key permanently into the bit
      bucket, so every connect is a first connect.
- [x] Its key-auth advice could produce the prompt its own rule forbids: the row said `ssh -i
      <keypath>`, and `-i` alone falls back to a password prompt on key rejection, hanging an
      unattended run. `BatchMode` and `PreferredAuthentications` appeared NOWHERE in the file.
- [x] RED on a weak literal tier, and the baseline's own attributions are the evidence: it took
      `/dev/null` from the skill's line 51, but cited "Memory:" - not the skill - for BatchMode and
      PreferredAuthentications. It then worked around the consequence with `2>/dev/null`, discarding
      stderr entirely, which its own gaps list flagged as bad for debugging.
- [x] GREEN on the same tier and scenario, with every option required to quote a line of THAT FILE
      or say NONE. All six options cited the file; no "Memory" attribution remained.
- [x] Diffed GREEN against RED in BOTH directions - nothing the baseline produced was lost; the
      option list is the same shape with the known-hosts path corrected and the auth options now
      sourced from the skill.
- [x] GREEN's gaps list worked as REFACTOR input: it reported that a command-line
      `StrictHostKeyChecking=no` has no scope, while the prose says to scope it to the subnet. Real,
      security-relevant, and exposed by this edit - closed by stating that the inline flag weakens
      every host it is aimed at, preferring the config block, and otherwise requiring the script to
      refuse an out-of-range target. Four other gaps DECLINED with reasons (chmod 600 and key
      readability are already stated elsewhere in the file; absolute paths and config-vs-inline for
      cron are generic cron concerns this skill does not own).
- [x] Verified no `UserKnownHostsFile=/dev/null` recommendation survives anywhere: the remaining
      `/dev/null` occurrences are stream redirects (`2>/dev/null`, `</dev/null`) or the cause being
      named deliberately.
- [x] Subnet examples use the RFC 5737 reserved documentation ranges, not the real ones the file
      previously carried.
- [x] Knowledge only - the local `sshf.py` wrapper is NOT shipped: it hardcodes an internal
      credentials path, account name and key filename across seven lines, which would publish
      internal infra naming and would not work for anyone else.
- [x] No session narrative or private provenance added.
