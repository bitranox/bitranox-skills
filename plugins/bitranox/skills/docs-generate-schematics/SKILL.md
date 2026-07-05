---
name: docs-generate-schematics
description: Use when a document, paper, poster, or README needs a scientific schematic, flowchart, block diagram, or architecture figure GENERATED as an image from a text description via an AI image model - CONSORT participant flows, neural-network architectures, pipeline diagrams - using OpenRouter (OPENROUTER_API_KEY) with an automated quality-review loop. Not for converting existing documents (bitranox:docs-convert-markitdown) or code-rendered graphs (graphviz/matplotlib).
---

# Generating scientific schematics with an AI image model

> Adapted from the MarkItDown skill in K-Dense-AI/claude-scientific-skills (MIT). See THIRD_PARTY_NOTICES.md.

Generate publication-style schematic images (flowcharts, block diagrams, architecture
figures) from a text description. The AI variant runs an iterative quality loop: generate,
have a vision model critique the result against the document type, regenerate until the
quality threshold or the iteration cap is hit.

## Requirements

- `OPENROUTER_API_KEY` in the environment (both scripts talk to OpenRouter).
- `httpx2` for the AI script (PEP-723/uv handles it; the wrapper is stdlib-only).

## Usage

```bash
# AI generation with quality-review loop
python3 scripts/generate_schematic_ai.py "CONSORT participant flow for a two-arm RCT" -o flow.png
python3 scripts/generate_schematic_ai.py "Neural network architecture diagram" -o arch.png --iterations 2
python3 scripts/generate_schematic_ai.py "Simple block diagram" -o diagram.png --doc-type poster

# Thin wrapper (single shot, no review loop)
python3 scripts/generate_schematic.py "Data pipeline overview" -o pipeline.png
```

`--doc-type` tunes the acceptance threshold (a poster tolerates less detail than a paper
figure); `--iterations` caps the regenerate loop.

## Common mistakes

- Expecting deterministic output - image models vary run to run; keep the prompt specific
  (name the boxes, arrows, and labels you need) and review the result yourself.
- Using this for graphs that should be code-rendered - reproducible plots and graphs belong
  in graphviz/matplotlib, not an image model; this skill is for illustrative schematics.
- Committing the generated image without checking the labels - vision-model review catches
  layout problems, not domain wording.
- Running without `OPENROUTER_API_KEY` - both scripts fail fast; set it in the environment,
  never on the command line.
