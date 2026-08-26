# Presets: backing them up, writing them, keeping them

## Back up first, always

Do this BEFORE migrating. Migration can empty the account's stored presets, and if that happens the
only copy left is this backup.

```bash
uv run scripts/soundtouch_presets.py backup --ip <speaker-ip> --outdir ./backup
```

Or by hand, straight from the speaker:

```bash
curl -s http://<speaker-ip>:8090/presets > presets-backup.xml
curl -s http://<speaker-ip>:8090/info    > info-backup.xml
```

Check the file has the number of presets the owner expects. Never retype values out of a terminal:
the locations carry query strings that a wrapped terminal line silently truncates.

## Why a preset that looks right never plays

A `LOCAL_INTERNET_RADIO` preset's `location` does NOT mean "play this URL". The speaker FOLLOWS the
location and expects a station document describing the stream. Give it the stream URL itself and it
receives audio where it expected a document, holds the source about twenty seconds, and discards it
without ever buffering.

The service provides the document at its playback adapter:

```
http://<service-host>:8000/custom/v1/playback/<base64url-of-stream-url>?name=<name>
```

The encoding is URL-safe base64 WITH padding.

Right:

```xml
<ContentItem source="LOCAL_INTERNET_RADIO" type="stationurl"
             location="http://<service-host>:8000/custom/v1/playback/aHR0cHM6Ly8...?name=Example%20Radio"
             sourceAccount="" isPresetable="true"><itemName>Example Radio</itemName></ContentItem>
```

Wrong, and accepted at write time:

```xml
location="https://radio.example.com/stream"
```

This is what `/now_playing` tells you:

| What you see                                 | What it means                              |
|----------------------------------------------|--------------------------------------------|
| source set, no play status, gone after ~20 s | the location is a raw stream URL           |
| buffering, then gone after ~20 s             | the format is right, the audio never came  |
| buffering, then playing                      | correct                                    |

Reaching the buffering state is the proof that the preset format and the service are both right.

## Why presets vanish on every reboot

The speaker asks its account for presets about two seconds after boot, but does not mount the radio
source until about seventy seconds later. Presets naming a source that does not exist yet are
discarded. The speaker then sends its now-EMPTY preset set back to the service, overwriting the good
copy there. That second half is what makes the loss permanent instead of temporary.

This is firmware behaviour. It cannot be fixed on the speaker, and there is no setting for it.

The fix is a canonical copy kept off the speaker, rewritten after the source has mounted. One JSON
file per speaker, named by device id:

```json
{
  "deviceId": "0000005E005300",
  "name": "Example Speaker",
  "presets": [
    {
      "buttonNumber": 1,
      "name": "Example Radio",
      "location": "https://radio.example.com/stream",
      "contentItemType": "stationurl",
      "source": "LOCAL_INTERNET_RADIO"
    }
  ]
}
```

The `location` here is the PLAIN stream URL. The script builds the playback-adapter wrapping when it
writes, so the service moving to another address never means editing these files.

```bash
uv run scripts/soundtouch_presets.py check                     # reports, never writes
uv run scripts/soundtouch_presets.py restore --confirm         # writes what is missing
```

### Putting it on a timer

Restoring once by hand fixes today and nothing else. The restore has to run on a schedule, or the
presets vanish again at the next power cut. Ask which system the service runs on and set it up:

| System               | How                                                                        |
|----------------------|-----------------------------------------------------------------------------|
| Linux, Raspberry Pi  | `crontab -e`, then a line: `*/2 * * * * cd /path/to/skill && uv run scripts/soundtouch_presets.py restore --ip <speaker-ip> --template <file> --service <service> --confirm` |
| Linux with systemd   | A `.service` plus a `.timer` with `OnBootSec=3min` and `OnUnitActiveSec=2min`, `Persistent=true` |
| Synology, QNAP       | The Task Scheduler in the web interface, a user-defined script every 2 minutes |
| Windows              | Task Scheduler, a basic task repeating every 2 minutes                       |
| macOS                | A launchd agent with `StartInterval` 120                                     |

Every two minutes is deliberate. It is a no-op when the presets are already correct, and it
deliberately does nothing while the radio source is not mounted, because writing in that window is
silently undone by the same wipe.

Check afterwards that it is actually running, rather than assuming: wait for the next slot and look
for a change, or run the `check` subcommand and confirm it reports nothing missing.

Tell the owner what to expect: after a power cut the presets come back by themselves within a few
minutes, not instantly. If they never come back, the timer is not running.

## Acceptance: listen, do not count

Counting presets proves they were written, not that they play.

1. Turn the volume down first.
2. Play one preset and watch until it reaches the playing state.
3. Play a DIFFERENT preset and watch again. One working station does not prove the set works.
4. Put the volume back.
5. Reboot, wait three minutes, and check the presets returned on their own.

When checking that a second preset played, require the station NAME to change. Waiting only for the
playing state passes instantly when the speaker is already playing the previous preset, which proves
nothing at all.
