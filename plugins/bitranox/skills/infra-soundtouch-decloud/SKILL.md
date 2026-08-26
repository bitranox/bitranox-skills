---
name: infra-soundtouch-decloud
description: Use when Bose SoundTouch speakers lost internet radio and presets after Bose shut down the SoundTouch cloud, when setting up a self-hosted replacement service for them, when a speaker is not discovered on the network, when presets disappear after every reboot or a preset is accepted but never plays, when a speaker needs telnet or SSH access enabled, or when its service URLs still point at streaming.bose.com.
---

# Bose SoundTouch without the Bose cloud

Bose shut the SoundTouch cloud down. The speakers keep AUX, Bluetooth and Alexa; internet radio,
presets and browsing are dead until they are pointed at a replacement service you run yourself.

This skill walks an owner through that end to end. Assume the owner is NOT technical: ask, do not
instruct, and ask for the physical things only they can do.

## The two rules that decide the outcome

**Read freely, confirm every change.** Discovery, state, backups and verification run unattended.
Rooting a speaker, rewriting its service URLs, rebooting it and writing presets are explained in
plain words and need a yes first. Say what will change and what it will look like afterwards.

**Order is load-bearing.** Back up the presets BEFORE migrating. A speaker asks its account for
presets about two seconds after boot but does not mount the radio source until roughly seventy
seconds later, so presets arriving in that window are discarded and the speaker then pushes its
now-empty set back, overwriting the copy on the service. Migrating first can therefore destroy the
only copy of the presets.

## The walkthrough

Ask one question at a time. Prefer multiple choice. Check in after each phase.

| Phase | Do this                                                                    | Detail in            |
|-------|----------------------------------------------------------------------------|----------------------|
| 1     | Ask which speakers and models. Warn about stereo pairs before anything else | this file, below     |
| 2     | Decide where the service runs and PIN that address                          | service-setup.md     |
| 3     | Check Docker is installed; if not, walk them through installing it          | service-setup.md     |
| 4     | Start the container with host networking, verify it answers                 | service-setup.md     |
| 5     | Find the speakers; ask the owner to wake any that do not answer             | service-setup.md     |
| 6     | Back up every speaker BEFORE any change                                     | presets.md           |
| 7     | Enable telnet/SSH access where the procedure needs it, and make it persist  | access-and-rooting.md|
| 8     | Rewrite the four service URLs, verify nothing cloud is left                 | migration.md         |
| 9     | Wait for the radio sources; bind the account if they never mount            | migration.md         |
| 10    | Write the presets and keep them across reboots                              | presets.md           |
| 11    | Acceptance: hear two different stations, reboot, check they came back       | presets.md           |

**Phase 1 warning, before anything else.** If two speakers are configured as a STEREO PAIR, break
the pair first. De-clouding a paired speaker risks bricking it, and this is reported for the ST10 in
particular. Ask explicitly: "are any two of your speakers set up as a left/right stereo pair?"

## Reference files

Use the Read tool to load the file for the phase you are in. Do not answer from this table alone.

| Topic                                                                                     | File                   |
|-------------------------------------------------------------------------------------------|------------------------|
| Docker check and install per OS, compose file, host networking, env, discovery, waking a speaker | references/service-setup.md |
| Diagnostic port 17000, the rooting methods per firmware, making SSH survive a reboot      | references/access-and-rooting.md |
| The four service URLs, the write order, verification, binding an account                  | references/migration.md |
| Preset location format, the boot wipe, restore loop, backup, the JSON template            | references/presets.md  |
| Symptom to cause, the diagnostic one-liners, how long each step takes, upstream docs       | references/troubleshooting.md |

## Scripts

Run with `uv run scripts/<name>.py`. Each prints a JSON envelope; exit 0 yes, 1 no, 2 error.
Anything that CHANGES a speaker requires `--confirm`, so the read half is always safe to run.

| Script                  | Use it to                                                            |
|-------------------------|-----------------------------------------------------------------------|
| `soundtouch_service.py` | Check Docker, write and validate the compose file, check service health |
| `soundtouch_find.py`    | Discover speakers and report what state each is in                    |
| `soundtouch_onboard.py` | Back up, open access, migrate the URLs, reboot, prove a preset plays  |
| `soundtouch_presets.py` | Back up, template, restore and check presets                          |

## When it does not work

Work `references/troubleshooting.md` first: it maps each symptom to its cause, and most reports land
on one of four causes. If the symptom is not there, or the fix does not hold, READ THE UPSTREAM
DOCUMENTATION rather than guessing - the project is actively developed and its guides move ahead of
any local copy:

- Troubleshooting: `https://github.com/gesellix/bose-soundtouch/blob/HEAD/docs/content/docs/guides/TROUBLESHOOTING.md`
- All guides: `https://github.com/gesellix/bose-soundtouch/tree/HEAD/docs/content/docs/guides`
  (GETTING-STARTED, MIGRATION-GUIDE, MIGRATION-SAFETY, DEVICE-INITIAL-SETUP, SELF-HOSTING,
  RASPBERRY-PI, HTTPS-SETUP, MUSIC-SERVICES, SURVIVAL-GUIDE)
- Open issues, for a symptom that looks like a bug rather than a misconfiguration:
  `https://github.com/gesellix/bose-soundtouch/issues`

Fetch the page and act on what it says. Tell the owner plainly when a problem is a known upstream
issue rather than something they did wrong.

## Common mistakes

| Mistake                                                | What happens                                                        |
|--------------------------------------------------------|----------------------------------------------------------------------|
| Bridge networking, or adding a `ports:` block           | Service answers HTTP and discovers nothing. Looks installed, is useless |
| Migrating before backing up the presets                 | The speaker's empty set overwrites the service copy; presets are gone |
| Rewriting only the account URL                          | Presets sync and nothing ever plays                                  |
| Writing the persisting command before the others        | Every value reverts at the next reboot although each replied OK      |
| Skipping the flash marker after opening SSH             | Access is gone at the next boot and looks like it never worked       |
| Putting the raw stream URL in a preset                  | Accepted at write time, never plays                                  |
| Letting the service's address come from plain DHCP      | Every speaker breaks at once, weeks later, when the lease changes    |
| Declaring failure 30 seconds after a reboot             | Radio sources need roughly 80 seconds; presets need 2 to 3 more minutes |
