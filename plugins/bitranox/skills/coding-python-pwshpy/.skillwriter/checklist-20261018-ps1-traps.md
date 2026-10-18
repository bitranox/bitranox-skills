# skill-writer checklist - coding-python-pwshpy (2026-10-18, ps1-traps)

- [x] Change: a new section "Still writing a `.ps1`? Six traps" between the translation section and
      `pwshpy pack`: a three-column table (trap, shells, do instead) for an advanced script eating a
      forwarded `-v`, a function returning its narration with the value, the `curl` alias, native
      stderr as error records under `Stop`, `pwsh -File` splitting `--out=C:\data` at the colon, and
      an unguarded pre-lock read probe; plus one line on how to test a forwarding wrapper.
- [x] Every row measured on a Windows guest with one probe script run under both shells
      (Windows PowerShell 5.1.26100, pwsh 7.6.6): advanced script binds `-v` (both); function
      returns `Object[]` of 2 (both); `curl` alias to Invoke-WebRequest (5.1 only, none on 7);
      `2>&1 | ForEach-Object` under Stop throws NativeCommandError on 5.1 and passes on 7;
      `-File ... --out=C:\data` arrives as 2 arguments on 7 and 1 on 5.1; Get-FileHash on a file
      held with FileShare.None throws under Stop (both). The Shells column states exactly that.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route recorded: `redcheck --corpus-cascade` reported INHERITED COVERAGE naming the two
      memory facts this change folds, so a behavioural RED cannot fail honestly. Replaced by a text
      check of the artifact: before the change the skill held none of the six (grep for
      `curl.exe`, `CmdletBinding`, `Write-Host`, `2>&1`, `Get-FileHash`, `-File`: no hit).
- [x] GREEN quote-back on opus and haiku, seven questions (forwarded `-v`, narration plus exit
      code, `curl` on 5.1, stderr pipe on 7.6, `powershell.exe -File` with a colon, pre-lock hash
      probe, and a scope control: list services -> use pwshpy): 14 of 14 answers correct, each with
      a quote of the governing cell or sentence.
- [x] Gaps closed after GREEN: the heading said "fail silently" while two rows fail loudly (now
      "Six traps"); the text never said a 5.1-only trap is absent on 7 (now stated); a caller that
      needs the exit code back (narrate with `Write-Host` so the value is the only output); "check
      what the tool did" named no method (now `$LASTEXITCODE` and the tool's result). Re-tested on
      haiku for the four questions the fixes touched: 4 of 4 quoted.
- [x] Gaps declined: a code example forwarding `$args` to a native exe (native argument passing
      differs between 5.1 and 7 and was not measured here); a lock primitive (out of scope); what to
      do where pwshpy cannot be installed (the existing `pwshpy pack` section); whether bare
      `2>&1` without a pipe dies on 5.1 (not measured); the H1 `using-pwsh` (the tool repo's skill
      name, kept identical in both copies by convention).
- [x] GREEN diffed against RED both ways: no existing section changed, so nothing was lost; the
      scope control still answers "use pwshpy".
- [x] Description measured: unchanged (616 characters).
- [x] Mirror: the same hunk applied to the pwshpy repo's `skills/using-pwsh/SKILL.md`; the section
      is byte-identical between the two.
- [x] Security scan: prose only; example paths are `C:\data` and `example.com`; no secrets,
      hostnames or addresses.
