# bitranox-skills

**A Claude Code plugin that learns your way of working.** It notices when a session teaches
something - a correction, a rule you state, a mistake worth not repeating - captures it as durable
memory, sleeps on it, and files each lesson exactly where it applies: this project, this group of
projects, or everything you do. On top of that self-learning memory it ships **58 skills** of
software-engineering craft - planning, debugging, code review, clean architecture, language and
tool references, humanizing prose - refined over real day-to-day work and growing with every
lesson that proves broadly useful.

The result compounds: the same correction is never made twice, knowledge from one project is on
the desk when a sibling project needs it, and routines harden into skills instead of being
re-derived every time.

## Quick start

```text
/plugin marketplace add bitranox/bitranox-skills
/plugin install bitranox@bitranox-skills
```

Install at **user scope** (the default) - the memory files lessons across projects, so it must
run everywhere. Then enable auto-update once via `/plugin` -> **Marketplaces** ->
`bitranox-skills` -> **Enable auto-update**. Windows needs
[Git for Windows](https://gitforwindows.org/); details and verification in
[docs/installation.md](docs/installation.md).

Skills are invoked as `/bitranox:<skill>`, and Claude picks one up automatically whenever a task
matches its description.

## The book

| Chapter                               | What it answers                                                                      |
|---------------------------------------|--------------------------------------------------------------------------------------|
| [Concepts](docs/concepts.md)          | The ideas: learn as you go, sleep on it, file knowledge by reach - in plain language |
| [Installation](docs/installation.md)  | Install, auto-update, Windows, verifying the setup                                   |
| [Setup](docs/setup.md)                | First-session decisions: knobs, tree shape, iron rules, seeding a project            |
| [Usage](docs/usage.md)                | The daily flow: capture, recall, the nap/tree/crosstree consolidation ladder         |
| [Skill catalog](docs/skills.md)       | All 58 skills with their triggers, grouped by domain (generated, cannot rot)         |
| [Architecture](docs/architecture.md)  | Store format, the write engine, the hook pipeline, guards, delivery paths            |
| [Reference](docs/reference.md)        | Every knob, sentinel file, env var, CLI command, and quirk                           |
| [Contributing](CONTRIBUTING.md)       | Authoring skills, the quality gates, proposing changes upstream                      |
| [AI transparency](ai-transparency.md) | Where AI is used in this repo, what is verified, and how to check it yourself        |

## Repo layout

This repo is both the marketplace (`.claude-plugin/marketplace.json`) and the single plugin it
ships (`plugins/bitranox/`): the skills live in `plugins/bitranox/skills/`, the hooks in
`plugins/bitranox/hooks/`.

## Credits

Most skills are custom-built or adapted. Some general workflow skills (brainstorming,
systematic-debugging, test-driven-development, verification-before-completion) originate from
public skill libraries (for example Obra Superpowers and the Vercel Agent Skills Directory) and
have been adapted here. `markitdown` and `rory` build on upstream sources (the MarkItDown
document converter and Rory Sutherland's public talks and writing, respectively). Skills adapted
from a third-party source under a permissive license carry their original copyright and license
text in [`plugins/bitranox/THIRD_PARTY_NOTICES.md`](plugins/bitranox/THIRD_PARTY_NOTICES.md).

## License

MIT - see [`LICENSE`](LICENSE). Adapted third-party skills retain their own permissive licenses;
see [`plugins/bitranox/THIRD_PARTY_NOTICES.md`](plugins/bitranox/THIRD_PARTY_NOTICES.md).
