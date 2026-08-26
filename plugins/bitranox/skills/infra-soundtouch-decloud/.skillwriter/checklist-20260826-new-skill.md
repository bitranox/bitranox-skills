# skill-writer checklist - infra-soundtouch-decloud (new skill)

A hub skill that walks a non-technical owner through replacing the shut-down Bose SoundTouch cloud
with a self-hosted service: standing the container up, finding the speakers, opening access where
the procedure needs it, rewriting the four service URLs, and keeping presets across reboots. Ships
five scripts and 69 tests.

## PLAN

- [x] Skill type: hub with reference files, driving an interactive procedure. Test approach:
      application scenarios, three of them, each an owner describing a symptom in their own words.
- [x] Prior art surveyed across the catalogue: no skill mentions SoundTouch, telnet, or device
      access. Four adjacent skills are cross-referenced rather than duplicated
      (coding-python-network-probe, compuse-ssh, net-firewall-pfsense, infra-proxmox).
- [x] Scope: SKILL.md as an index, five reference files, `scripts/` and `tests/` as siblings.
- [x] Category `infra` per the taxonomy registry; sub-prefix `soundtouch`.

## RED

- [x] Contamination checked before trusting the baseline. `redcheck --corpus-cascade` reports
      INHERITED COVERAGE, but its evidence is function-word overlap only (`going`, `gone`, `walk`,
      `comfortable`), so it is a false positive. The direct check is the one relied on: the CLAUDE
      chain above the working directory mentions Bose only as a directory name, the two memory
      facts that match teach an unrelated shell trap and file modes, and the repos holding the
      procedure are on a sibling branch that a dispatched agent does not inherit. A grep control
      returning 6 hits for an unrelated term confirms the search itself works.
- [x] Three scenarios run with no skill present, on an inert probe agent pinned to a weak tier.
- [x] Baseline 1 (presets vanish after every power cut) answers with a wrong mechanism stated
      confidently: "your presets are disappearing because they're being stored in the speaker's
      temporary memory (RAM) instead of permanent storage", and prescribes a setting that does not
      exist: "Is there a 'save presets to speaker' or 'persist settings' option ... that needs to be
      enabled?"
- [x] Baseline 2 (nothing plays) blames DNS and content reachability, directs the owner to read
      preset URLs from a speaker web interface "on port 80 or 8080" (it is 8090), and never reaches
      either real cause.
- [x] Baseline 3 (set the service up) is the most damaging: it invents three container images
      (`artificialignorance/soundtouch`, `bose-soundtouch-api`, `soundtouch-emulator`), and emits a
      compose file with a `ports:` block on a `bridge` network, which is the one configuration
      documented as unable to discover a speaker. It also invents a "Server Address" setting on the
      speaker and offers DNS spoofing.
- [x] Pattern across all three: confident, plausible, wrong, and no baseline reaches the ordering
      constraints that decide whether any of the work survives a reboot.

## GREEN

- [x] Same three scenarios with the skill present. All three now produce the correct diagnosis and
      the correct action.
- [x] Quote-back required and passed on all three; none answered NONE. Scenario 1 quotes the boot
      race and the empty-set overwrite verbatim; scenario 2 quotes both the symptom row and the
      location rule; scenario 3 quotes the host-networking paragraph and the loopback rule.
- [x] Scenario 3 additionally leads with the stereo-pair warning before any step, asks which address
      will be pinned, and stops to ask before changing a speaker - the confirm-every-change rule
      reaching behaviour rather than only text.
- [x] Every dispatch, both arms, asked for a `Skill gaps` section.

## REFACTOR

Diffed GREEN against RED in both directions. Nothing the baselines produced is lost: their content
was wrong in every case, and each GREEN answer is a superset of the useful part.

Gaps reported by GREEN and their disposition:

- [x] CLOSED - the restore is described as running "on a timer" with no way to create one. A timer
      table now covers cron, systemd, Synology and QNAP, Windows Task Scheduler and launchd, plus
      how to confirm it is really running.
- [x] CLOSED - the data directory is used without being created. The compose section now creates it
      and says any path works.
- [x] CLOSED - no way to create the compose file. A heredoc is shown.
- [x] CLOSED - how to read the machine's MAC for a DHCP reservation. Three commands added.
- [x] CLOSED - what to do when `docker compose` needs sudo. Stated explicitly.
- [x] DECLINED - per-router instructions for a DHCP reservation. Routers differ too much to
      enumerate and the list would rot; the skill instead names where the setting usually lives and
      that it works by MAC.
- [x] DECLINED - which replacement project the owner runs. The skill names the project it is written
      for; guessing at forks is out of scope.
- [x] Scenario 2 reported no gaps. Its answer is verified by quote-back rather than by its own
      report, and it used the documented discriminator between the two causes that both present as
      "nothing plays".

## Quality

- [x] Frontmatter parses; `name` and `description` only. Description measured at 411 characters,
      trigger-first, no workflow summary.
- [x] SKILL.md is an index at 1017 words; detail lives in five reference files.
- [x] Routing table lists a distinct topic per file; no two rows compete for the same query.
- [x] Every address is a reserved documentation range (192.0.2.0/24, 198.51.100.0/24) or a
      deliberate loopback used as a negative example. No MAC, device id, account number, SSID,
      hostname or personal path from any real installation appears. Verified by grep over every
      file.
- [x] Present tense throughout; no session narrative, no provenance, no scratch paths.
- [x] Scripts are standard library only, so the test modules import in a bare environment.
- [x] `tests/` covers every script: 69 tests, all passing.
- [x] Every subcommand that changes a speaker requires `--confirm`.
- [x] External documentation references resolve: the upstream guides directory and TROUBLESHOOTING
      path were fetched and confirmed to exist, and are linked branch-agnostically.
- [x] Security review of the whole diff: no credentials, no private hosts, no `shell=True`, no
      `eval`. `http_get` refuses a non-http scheme so a `file:` URL cannot read local files, and
      that refusal is tested.
