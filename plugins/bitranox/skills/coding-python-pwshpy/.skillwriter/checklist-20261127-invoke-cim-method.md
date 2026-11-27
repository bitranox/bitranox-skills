# Checklist 2026-11-27: invoke_cim_method (pwshpy 1.13.0 mirror)

Mirror of the tool repo's skill change for its new API: a cmdlet-table row and a section on
reading values WMI exposes only as method results through the read-only `invoke_cim_method`.

Decisions: none - mirror of a tool-repo API addition, the text states the API and decides no rule

## PLAN

- [x] Skill decisions read first: the ledger has no entries for this skill.
- [x] Type: reference skill; test approach: retrieval.

## RED

- [x] Text check at HEAD: `invoke_cim_method` and `Invoke-CimMethod` 0 hits, so the old text has no
      answer to "how do you read BitLocker EncryptionPercentage with pwshpy".

## GREEN

- [x] Text check on the new text: `invoke_cim_method` 9 hits; the cmdlet table row and the section
      name `GetConversionStatus` and read `EncryptionPercentage` from `out_parameters`.
- [x] The section's first example executed on a real Windows host against the 1.13.0 wheel:
      `GetConversionStatus`, `GetLockStatus`, `GetKeyProtectors` and the five `Win32_Tpm` methods
      returned `return_value` 0 with the documented out-parameters; `Encrypt` raised
      `CimMethodNotAllowedError`. The host's volume has no key protectors, so the
      `GetKeyProtectorType` loop ran over an empty list; that branch is covered by the tool repo's
      unit tests only.
- [x] No subagent probe: subagents were unavailable on this account when this change was made, so
      the coverage check against the file is the evidence and routing stays unverified.

## REFACTOR

- [x] Twin identical apart from the `name:` line (difflib over both files: 2 differing lines).
- [x] ASCII check over the added lines clean; no host name, address or private path added.
