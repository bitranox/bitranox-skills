# skill-writer checklist - coding-python-pwshpy (memory rules folded in)

- [x] Change: ## Still writing a `.ps1`? Eight traps (table row + note paragraph after the table;
      heading Six->Eight and intro sentence amended) - coding-python-pwshpy/SKILL.md. RED on the
      pre-edit snapshot: NONE. Verified: Culture behaviour -> local pwsh 7.6.3 probe with
      CurrentCulture='de-DE', $v=[math]::Round(476978880102/1GB,1): output 'interp: FREEGB=444.2',
      'concat: FREEGB=444.2', 'format: FREEGB=444,2', 'tostring: FREEGB=444,2', 'writehost-args:
      FREEGB= 444,2', bare 'Write-Output $v' -> '444,2', Out-String -> '444,2',
      '$v.ToString([Globalization.CultureInfo]::InvariantCulture)' -> '444.2';
      '[cultureinfo]::InvariantCulture' accelerator -> '444.2'. Twins identical before edit -> diff
      -r shows only name field (2c2) + .skillwriter. Table fit -> each new cell measured <= existing
      column width (183/192, 9/41, 135/138); reformat_tables.py --check --strict SKILL.md ->
      'Unchanged' rc=0. No anchor links to 'six-traps' anywhere (grep). Added lines ASCII-only,
      <=100 cols, history-wording finder clean.
- [x] Dropped as stale or unverified: Skeptic/hint claim that '[math]::Round' output as such uses
      the culture is imprecise: measured, interpolation and string concatenation are invariant
      (444.2); only -f, .ToString(), Write-Host separate args and bare/default output use the
      culture, so the text names those forms. 'Get-Process CPU' example dropped (not re-verifiable,
      covered by 'bare output'). Private fleet name, VM id, InstallLanguage 0407 and the dated
      2026-08-22 measurement dropped. 5.1 behaviour not measured here (no Windows host): the note
      states 'measured on pwsh 7'; intro sentence amended so the 'checked on 5.1.26100 and 7.6.6'
      claim does not cover this row.
- [x] Change: ## Still writing a `.ps1`? Eight traps (table row + note paragraph after the table) -
      coding-python-pwshpy/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: SID form
      '*S-1-5-32-544:(OI)(CI)F' -> matches infra-windows-servicing/SKILL.md house form (skeptic,
      :190). Well-known SIDs -> pwshpy src/pwshpy/domain/enums.py:341 'ADMINISTRATORS =
      "S-1-5-32-544"'. add_acl_ace SID -> pwshpy src/pwshpy/composition/facade.py:982 'On Windows
      ``trustee`` is a SID string or name'. 1332 = ERROR_NONE_MAPPED (Win32 constant; message text
      standard). Whole-command refusal, no grants/inheritance change, rc 1332, SID arm rc 0 -> fact
      body's measured A/B on a German host (kept as observed behaviour, no Windows host reachable
      read-only). cmd '&' unconditional vs '&&' -> standard cmd semantics. Add-LocalGroupMember -SID
      -> documented LocalAccounts cmdlet parameter set (not runnable here). Table fit and canonical
      form verified with reformat_tables.py --check --strict (rc 0). German error text quoted only
      up to its ASCII prefix so it stays ASCII and still greps a real log.
- [x] Dropped as stale or unverified: Hint's 'same for net localgroup Administrators' implied SID
      remedy dropped (net localgroup takes no SID); replaced with Add-LocalGroupMember -SID. 'run it
      from a .ps1 (a private helper)' dropped (private helper). Host name, script name, private
      path, service account, 'for months' exposure and dated measurement dropped. Transliterated
      'durchgefuehrt' not used (would not match the real umlaut text).
- [x] Review C fixed: add_acl_ace accepts a SID string as the trustee; a name is looked up with
      LookupAccountName on the target machine and the English name of a built-in group fails there
      the same way (pwshpy raises instead of failing silently) (pwshpy
      src/pwshpy/adapters/native/acl_control.py _resolve_sid, sid.py sid_string).
- [x] Review C declined: a cross-reference from compuse-ssh for the decimal-comma rule. The fact
      keeps its short pointer, which fires where pwshpy is not loaded.
- [x] GREEN gap fixed: a local user account name is not localized and can stay a name; the read-back
      confirms every grant and, after /inheritance:r, no inherited (I) entry.
- [x] Gaps declined: how to capture the host's real bytes for a parser fixture (the rule says to
      test on them); exit-code checking from bash over ssh (owned by compuse-ssh).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (9 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
