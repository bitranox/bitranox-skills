# net-rotating-proxies: one large download split across proxies (design)

Backlog [40], GitHub issue #4. `proxy_pool.py run` hands each worklist item to an external
command, one proxy per attempt, so a ban halfway through one large file restarts the whole file on
the next proxy. This adds a `fetch` subcommand that owns one download end to end: byte-range
chunks spread over the rotating pool, a chunk cut off mid-transfer resumed from its offset, every
reply checked for being the right object, and the finished file verified.

Approved section by section with the user on 2026-11-01. Chosen over a `{range}` placeholder in
`run` (a cut chunk restarts from scratch, the identity check and the join stay with the user) and
over skill text only (the failure modes are described but not handled).

## 1. Shape and data flow

```
proxy_pool.py --store ./.proxies fetch URL -o FILE
    [--chunk-size 8M] [--workers 8] [--need 16] [--sha256 HEX]
    [--chunk-timeout 120] [--max-attempts-per-chunk 20]
```

1. **Probe, through a proxy** (the local IP is the blocked one): `GET` with `Range: bytes=0-0`.
   A `206` with `Content-Range: bytes 0-0/TOTAL` gives the size and proves Range works; the
   `ETag` and `Last-Modified` of that reply are the object's identity. A `200` without
   `Content-Range` means the server ignores Range: fetch falls back to one whole-file stream per
   attempt, rotating proxies, with no resume, and says so.
2. **Plan**: split `0..TOTAL-1` into `--chunk-size` ranges; preallocate `FILE.part` at full size;
   keep a manifest `FILE.part.json` (url, total, identity, bytes received per chunk), written
   atomically after each chunk makes progress.
3. **Download**: N workers pull unfinished chunks. Each takes a proxy from the existing
   `ProxyPool.acquire`, requests `Range: bytes=<start+received>-<end>`, and streams into its own
   file handle at its offset. The ranges are disjoint, so seek plus write per handle is safe on
   every OS (no `os.pwrite`, which Windows lacks).
4. **Finish**: every chunk complete, size equals TOTAL, `--sha256` matches when given, then
   `FILE.part` is renamed to `FILE` and the manifest deleted. A killed run resumes from the
   manifest when the URL and identity still match; a manifest that does not match is refused.

Exit codes follow `run`: 0 a verified file; 1 chunks still missing after their attempt budget;
2 cannot work (no proxies, bad arguments, a hash mismatch).

## 2. Failure handling

Every chunk attempt is classified once; the class decides the proxy's fate and the bytes'.

| What happened                                              | Proxy                                | Bytes received              |
|------------------------------------------------------------|--------------------------------------|-----------------------------|
| connect fails, or the proxy errors before any byte         | ban (bad.txt), as in `run`           | none                        |
| not the object: `200` to a ranged request, `Content-Range` | ban: it serves something else        | not written: headers are    |
| start/end/total wrong, `ETag`/`Last-Modified` differ       | (an injected page, a stale cache)    | checked before any write    |
| `403` / `407` / `429` / `5xx`                              | record a failure, rotate; flaky      | none                        |
|                                                            | eviction for this run, never bad.txt |                             |
| cut off mid-body (reset, read timeout, short body)         | record a failure, rotate             | KEPT; the next attempt asks |
|                                                            |                                      | for start+received          |
| body runs past the requested end                           | record a failure                     | written only up to the end  |
| chunk complete                                             | record a success, good.txt           | chunk done                  |

- **Attempt budget**: `--max-attempts-per-chunk` per chunk. A chunk that runs out stays missing,
  the run exits 1 and keeps `FILE.part` and the manifest for a later resume; one spent chunk
  does not stop the others.
- **End-of-run report by reason**, e.g. `chunks 512/512, attempts 731: banned 41, identity
  mismatch 6, throttled 120, cut mid-body 52`. Many identity mismatches across proxies point at
  an object that changed on the server; the report shows it, no heuristic guesses it.
- **Hash mismatch**: exit 2, the manifest is deleted so a rerun starts fresh, `FILE.part` stays
  for inspection. A resume over known-bad data would fail the same way again.
- **Without `--sha256` the guarantee is length plus identity only**: a proxy injecting bytes
  behind correct headers is undetectable. fetch prints a one-line warning when no hash is given,
  and the skill says to pass one whenever the publisher provides it.

## 3. Testing with local stand-ins

All on 127.0.0.1, no internet, no vendor pool.

- **Range server**: a threaded `http.server` serving deterministic bytes (every offset's content
  is known), `206` with `Content-Range`, `ETag`, `Last-Modified`; switches to ignore Range (the
  fallback) and to change its `ETag` (identity), and a request log.
- **Fault-injecting forward proxies**, one port per behaviour: clean, refuse the connection,
  `429` / `403`, cut the body after N bytes, an injected HTML `200`, a wrong `Content-Range`, a
  stall until the read timeout. The test store's `live.txt` lists their ports, so the real
  `ProxyPool` picks them up through its normal path. Verified 2026-11-01: httpx2 sends a plain
  `http://` target to a proxy as an absolute-form request (`GET http://host/path HTTP/1.1`), not
  `CONNECT`, so plain forward proxies are enough.

Tests, written first and watched to fail:

- clean pool: the file is byte-identical and `--sha256` passes;
- mixed pool: byte-identical file; dead and injecting proxies end in `bad.txt`, throttling and
  mid-body-drop ones do not;
- a chunk cut mid-body resumes from its offset: the server log shows the second request starting
  at `start+received` (a final-file comparison alone would also pass on a restart);
- a run killed partway resumes from its manifest and skips finished chunks; a mismatching
  manifest is refused;
- a server without Range support takes the whole-file fallback;
- a wrong `--sha256` exits 2, deletes the manifest, keeps `FILE.part`;
- a chunk that spends its attempts exits 1 and keeps `FILE.part` and the manifest;
- unit tests for the pure parts: chunk planning (last chunk shorter, TOTAL 0 and 1),
  `Content-Range` parsing, the classification table.

## Shipping

A new subcommand is a MINOR bump. Tests in `net-rotating-proxies/tests/`, run with CI's
dependency set (httpx2 included). SKILL.md gains a section on one large file across proxies,
written under meta-skill-writer with RED/GREEN probes.
