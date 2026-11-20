# checklist - registry keys take the hive form, never HKLM:\

One queued contribution. The cmdlet table's registry row shows the hive form, and a note under the
table says `get_item_property` and `registry_keys` take `HKLM\...`, `HKLM/...` or the long hive
name, and refuse the drive form with `Unknown registry hive: 'HKLM:'`. Same change in the twin
(pwshpy skills/using-pwsh).

Decisions: none - documents existing behaviour

## RED

- [x] Skill decisions read first: none rejected on registry.
- [x] Measured on pwshpy (fake_winreg backend): `HKLM:\SOFTWARE\Microsoft` -> NativeCallError
      "Unknown registry hive: 'HKLM:'"; `HKLM\...`, `HKLM/...`, `HKEY_LOCAL_MACHINE\...` -> ok.
- [x] Text check at HEAD: "Unknown registry hive" 0 hits.

## GREEN

- [x] Quote-back probe (haiku): port, refusal text and long-name acceptance answered by quotes.

## REFACTOR

- [x] Table re-padded by the formatter (one row changed); twin tables identical; ASCII check clean.
