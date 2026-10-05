# Skill-writer checklist: PDF figures never described, plus undated model IDs (2026-10-05)

Scope: `SKILL.md`, `assets/example_usage.md`, `references/api_reference.md`,
`references/file_formats.md`. Before, several examples built a `MarkItDown(llm_client=..., ...)`
and then called `.convert()` on a `.pdf` input, implying the figures in a scientific paper PDF
get AI descriptions; and several `llm_model=` literals (both OpenRouter and plain-OpenAI IDs)
carried no "checked on" date, unlike the file's own convention elsewhere. After: every PDF
example that previously implied figure description now says plainly that markitdown never sends
a PDF's images to an LLM (text extraction only), and every `llm_model` literal carries the same
dated comment the file already uses elsewhere.

## PLAN

- [x] Skill type: reference (API/usage documentation for a third-party library's bundled
      scripts). Test approach for a reference skill: verify the corrected claims against ground
      truth (the installed `markitdown` package's source, and the scripts' own code/tests),
      not a pressure scenario - there is no discipline rule here for an agent to resist, only a
      factual claim to get right.
- [x] Re-checked the claim against current code before writing anything: grepped the installed
      `markitdown` 0.1.x package (`uv run --with markitdown`) for `llm_client` across its
      converters. Only `_image_converter.py` and `_pptx_converter.py` reference it;
      `_pdf_converter.py` does not import or use it at all. Confirms the claim: a PDF's figures
      are never described, whatever `llm_client`/`llm_model`/`llm_prompt` are set to.

## RED (current text, ground-truth check)

- [x] `assets/example_usage.md` ("Scientific diagram analysis" example) built an LLM-equipped
      `MarkItDown` and called `md.convert("paper_with_figures.pdf")`, with no caveat - reads as
      "this describes the paper's figures", which the source code above disproves.
- [x] `assets/example_usage.md` ("Different Prompts for Different Files") built `scientific_md`
      with an LLM prompt specifically for "Describe scientific figures" and then called
      `scientific_md.convert("research.pdf")` - the same defect, in a second code block.
- [x] `assets/example_usage.md` (first AI section) called `OpenAI()` with no `base_url`, then
      used an OpenRouter-style model ID (`anthropic/claude-sonnet-4.5`) - a second, adjacent
      defect: that ID is not valid against the real OpenAI API.
- [x] `SKILL.md` ("Convert Literature for Review") built an LLM-equipped `md_ai` right after a
      PDF-conversion loop with no `.convert()` call shown - strongly implies continuing that loop
      with PDFs, the same misleading pattern.
- [x] Undated `llm_model=` literals confirmed by grep: `SKILL.md:393,431`,
      `references/api_reference.md:26` (table cell) and `:318`, and four `gpt-4o` instances in
      `references/file_formats.md` (lines ~121, ~201, ~469, ~492 before the edit).

## GREEN (the fix)

- [x] `assets/example_usage.md`: the diagram-analysis example now converts `"figure.png"` instead
      of a PDF, with an inline comment stating the PDF limitation; the client is built with the
      OpenRouter `base_url` instead of bare `OpenAI()`; the "Different Prompts" example keeps
      `scientific_md.convert("research.pdf")` (a legitimate mixed-input demo) but now carries a
      comment that the `llm_client` has no effect on that call's figures, and the PPTX example
      beside it is marked as the one where pictures ARE described.
- [x] `SKILL.md`: the `md_ai` construction now carries the same "PDF figures are never described"
      comment, pointing at `docs-generate-schematics` or page-image extraction as the alternative.
- [x] Every previously-undated `llm_model=` literal now carries `# a vision model as of 2026-09;
      see references/api_reference.md` (OpenRouter IDs) or `# a vision-capable OpenAI model as of
      2026-09` (`gpt-4o`), matching the file's own existing convention at other call sites.
      `references/api_reference.md`'s table cell was reworded to point at "Available Models
      below" instead of repeating a single dated ID inside a table row.

## Verification

- [x] Re-ran `grep -n "anthropic/claude\|llm_model\|gpt-4o"` across all four files after the
      edit: every `llm_model=` literal now carries either a dated comment or an adjacent "see
      Available Models" pointer.
- [x] `reformat-md-tables` (PostToolUse hook) reformatted the edited table in
      `references/api_reference.md` automatically; re-read the result, columns aligned.
- [x] `scripts/tests/` suite (`test_convert_with_ai.py`, `test_convert_literature.py`,
      `test_batch_convert.py`, `test_markitdown_scripts.py`) run with CI's dependency set:
      91 passed, 9 skipped - these doc-only edits touch no script behaviour the suite covers,
      and nothing regressed.

## Security and hygiene

- [x] Diff reviewed: prose and code-comment only, no secret, real hostname, address or private
      path added. The `api_key="your-openrouter-api-key"` placeholder already existed; untouched.
- [x] No frontmatter, `name`, or trigger-affecting text changed in any of the four files, so no
      derived catalog/trigger artifact needs regeneration for this change.
- [x] Added/changed lines are ASCII only.
