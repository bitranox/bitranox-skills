---
name: python-use-modern-libraries
description: Use when choosing a Python library for a task, writing new Python code that needs a dependency, or reviewing imports for dated defaults. Gives modern, well-maintained third-party picks (HTTP, JSON, XML, TOML, YAML, data models, enums, dates, compression, database, testing, type-checking) and what to avoid. For building/editing JSON/XML/YAML files specifically, see bitranox:edit-json, bitranox:edit-xml, bitranox:edit-yml. Public, mainstream defaults; adjust per project.
---

# Modern Python library choices

Default to current, well-maintained libraries over dated stdlib or legacy packages when the
better option is clear. Install third-party deps via `uv` (a tool with `uvx`, or a script with
PEP-723 inline metadata run by `uv run`). Libraries on this list are pre-approved: just use
them and let `uv` fetch them, no need to ask. These are general public defaults, not absolutes:
a project's own conventions win.

## Adding an entry

Before adding a library here, vet it: trustworthy (reputable maintainer or community, not a
typo-squat), common (widely adopted), and modern (actively maintained, current releases). Each
row must carry all three of: a short **description** of what it is for (in the `Use` cell), the
older library/libraries it **replaces** (in the `Avoid` cell), and **why** it is better (the
parenthetical note in the `Use` cell). Keep rows one line; do not add anyone's private or
in-house packages here.

If the new library overlaps in function with an existing entry, resolve it - never leave two
rows silently competing for the same job:
- **Both have a place:** keep both and make the distinction explicit - state when to use which
  and why (e.g. one streaming vs one one-shot, sync vs async, simple vs full-featured).
- **The new one supersedes the old:** only when you are sure, replace the old row with the new
  one, move the now-obsolete library into the new row's `Avoid` cell, and say why it was
  replaced.

## Quick reference

`Use` names the pick with a brief why; `Avoid` names what it replaces.

| Task                                       | Use                                                                  | Avoid                                          |
|--------------------------------------------|----------------------------------------------------------------------|------------------------------------------------|
| HTTP / REST                                | `httpx2` (HTTP/2; the new Pydantic-org successor to httpx) or httpx  | `requests`                                     |
| JSON                                       | `orjson` (fast, correct, bytes)                                      | `json` stdlib for hot paths                    |
| TOML                                       | `rtoml`                                                              | `tomllib`, `tomli`                             |
| YAML                                       | `ruamel.yaml` (round-trips comments)                                 | `PyYAML`                                       |
| XML                                        | `lxml` (XPath, schema validation, fast C parser)                     | `xml.etree`, `minidom`, `xmltodict`            |
| Domain models                              | `dataclasses`                                                        | bare `dict`                                    |
| Boundary validation (untrusted input)      | `pydantic`                                                           | hand-rolled parsing                            |
| Enums                                      | `IntEnum` / `StrEnum`                                                | plain `Enum`, magic strings                    |
| Terminal output                            | `rich`                                                               | `colorama` (fallback only)                     |
| TUI                                        | `textual`                                                            | `curses`                                       |
| Paths                                      | `pathlib.Path`                                                       | `os.path`                                      |
| Date / time                                | stdlib `datetime` + `zoneinfo` (tz-aware)                            | `pytz`, naive datetimes                        |
| Compression (streaming / web / high speed) | `isal` (igzip) - speed tuned, bigger files                           | `gzip` stdlib for throughput                   |
| Compression (archival, high ratio)         | `deflate` (libdeflate bindings, high ratio, smaller files, C-extension dependency)         | `gzip` stdlib            |
| .env files                                 | `python-dotenv`                                                      | manual parsing                                 |
| Database (ODBC)                            | `pyodbc`                                                             | raw ODBC bindings                              |
| Database (MySQL)                           | `mysql-connector-python` or `SQLAlchemy`                             | `PyMySQL`, `mysqlclient`                       |
| ORM / complex queries                      | `SQLAlchemy`                                                         | custom ORM, raw SQL for complex apps           |
| Testing                                    | `pytest`                                                             | `unittest`                                     |
| Type checking                              | `mypy`                                                               | none                                           |
| CLI args / parsing                         | `rich-click` (Click-based, rich-formatted --help; drop-in for click) | `argparse`, `optparse`, `getopt`, bare `click` |
| Subprocess                                 | `subprocess.run([...])` (argv list)                                  | `os.system`, `shell=True`                      |

## HTTP example (httpx2)

    import httpx2 as httpx          # API-compatible with httpx
    with httpx.Client(timeout=30.0, proxy="http://user:pass@host:port") as client:
        r = client.get("https://api.example.com/data")
        r.raise_for_status()
        data = r.json()

Use a `Client` for many requests (connection reuse), and `AsyncClient` under asyncio. Both
support `proxy=` / `proxies=`, `timeout=`, and HTTP/2.

## Notes

- Prefer a library over an external command-line tool: `httpx2` instead of shelling out to
  `curl`, stdlib/`orjson` instead of `jq`, `re`/stdlib instead of `grep`/`sed`. Libraries are
  the same on every OS; external commands may be missing or take different flags on Windows.
- Reach for stdlib when no third-party library is warranted (small glue, no hot path): the
  point is "best tool", not "most dependencies".
- Logging, CLI framework, and layered configuration are deliberately left to each project's
  own conventions rather than prescribed here.
