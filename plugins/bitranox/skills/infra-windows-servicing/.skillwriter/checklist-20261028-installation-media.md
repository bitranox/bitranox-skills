# skill-writer checklist - infra-windows-servicing (2026-10-28, installation media for a repair upgrade)

- [x] Change: new subsection "Finding the right installation media for a repair upgrade" under
      "Choosing the remedy": the target values the media must match and the `reg query` lines that
      read them, which Microsoft page or licensing portal offers which edition, direct ISO
      (`install.wim`) versus Media Creation Tool ISO (`install.esd`), unpacking on Linux, and
      slipstreaming the current CU into an exported single-edition WIM. Two older sentences in the
      same section were corrected on the way: "a build >= the target's" now says "UBR included",
      and the RestoreHealth `/Source:wim:...:1` example (index by position, contradicting the rule
      after it) now takes `<index>`, defined by edition match.
- [x] Claims checked against ground truth: a Microsoft 25H2 direct ISO read with a loop mount holds
      `sources\install.wim`, ten images of one build, index 1 `Core`, no Enterprise and no
      `CoreSingleLanguage`; a Server 2025 evaluation ISO lists only `ServerStandardEval` and
      `ServerDatacenterEval`; the five `reg query`/`echo` lines run over ssh against a Windows 11
      guest return `REG_SZ`/`REG_DWORD 0x...` as quoted; the Windows 11 and Windows 10 download
      pages state the 24-hour link, the per-language SHA-256 table and the multi-edition ISO. The
      pair comparison in the Build row matches pve-winrepair's WIM gate (`(build, spbuild) <
      (CurrentBuild, UBR)` refuses).
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the editing agent loaded the skill
      through the Skill tool before the commit.
- [x] RED: baseline-probe (no filesystem tools) on opus given the pre-edit "Choosing the remedy"
      section and a Windows 11 Pro de-DE 26200.9711 scenario. It answered NONE for which guest
      values to read and how, where to download, MCT versus direct ISO, and Enterprise/evaluation
      media; only partial quotes for the older-media case ("slipstreaming the current CU", no
      commands) and the index-1 trap. It also reported the `install.wim:1` example contradicting
      the index rule and "build" not saying whether UBR counts (both closed in this change).
- [x] GREEN: same scenario on opus and haiku with the edited text pasted; all six questions
      answered by direct quote on both tiers.
- [x] GREEN diffed against RED both ways: every partial RED quote (slipstream rule, index-by-edition
      rule) is still in the edited text; nothing the baseline answered was lost.
- [x] Gaps from GREEN closed: EditionID for Pro, ISO language selection, AMD64 means x64, UBR hex
      conversion, where DISM runs (a healthy Windows machine, elevated), build numbers of 24H2 and
      25H2, putting the serviced WIM back into the media, the final check as ">= the target's UBR"
      with `ServicePack Build` decimal, the x64 download section name, the `N` placeholder renamed
      `<index>` (it clashed with the N-edition suffix), the N edition defined, the Build row
      stated as a pair comparison.
- [x] Gaps declined: where the `.msu` and checkpoint CU come from - covered elsewhere in this skill,
      section "A cumulative update Windows Update will not offer" ("Fetching the .msu. The Update
      Catalog has no plain download link ..."); "Durations" and "Deleting a Windows.old" - covered
      elsewhere in this skill; a PowerShell ssh default shell - the text states the `cmd.exe`
      precondition; regional German variants such as de-AT - out of scope, `InstallLanguage` is the
      stated test; whether the Windows 11 page steers a Windows browser to the MCT - not verified,
      so not claimed.
- [x] Quote-back after the last fixes: opus (effort medium) and haiku re-asked the touched
      questions (EditionID for Pro, DISM host, where the WIM goes, final condition, the `<index>`
      meaning, checkpoint CU for 26200, AMD64, UBR counting); both tiers answered every one by
      direct quote. A final haiku probe on the two re-edited table rows (Edition, Build) quoted
      the N-edition definition and the pair rule, and judged 26200.8037 against 26200.9711 NOT
      acceptable and 26200.100 against 26100.9999 acceptable, both right. Its remaining gaps (how
      the image's build and edition are read, what to do on a failed check) are excerpt artifacts:
      the full section answers them ("inspect with `wiminfo` ... on Windows with `dism
      /Get-WimInfo`", "`/SourceIndex` is the target's edition as `dism /Get-WimInfo` ... lists it",
      "Then slipstream ..."), so declined as covered elsewhere in the skill.
- [x] Tiers and cells: RED opus x1; GREEN opus x1 + haiku x1; quote-back opus x1 + haiku x2.
- [x] Describes the latest release only: no version-history wording added.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose and commands only; no secrets, private hostnames or paths; addresses are
      Microsoft's public URLs, the example `0x25ef`/`10.0.26200` values and placeholder paths
      (`C:\work`, `D:\sources`, `/mnt/x`, `DEST`).
