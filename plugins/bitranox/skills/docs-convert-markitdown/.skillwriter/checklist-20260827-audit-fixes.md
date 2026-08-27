# skill-writer checklist - docs-convert-markitdown (2026-08-27, audit findings)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. Every claim was re-derived from
the INSTALLED markitdown 0.1.7 (current PyPI release) before anything was edited.

Why a behavioural RED does not apply here: these are FACTUAL corrections to a reference skill that
is installed on this machine, so a subagent would answer from the installed wording rather than
from the file under test. The evidence is executed instead - real signatures, and the documented
code run verbatim. The strongest item below is a behavioural test, and it is what a RED would have
been for: the API as documented does not error, it silently does nothing.

- [x] WRONG - the OCR claim, which was broader than filed. markitdown 0.1.7 has NO OCR code path:
      a recursive grep for `tesseract|pytesseract|ocr` over the installed package returns only two
      comments inside the Azure Document Intelligence converter, which is a REMOTE service.
      `ImageConverter.convert` does exactly two things - EXIF metadata via `exiftool_metadata()`,
      and an optional LLM description when `llm_client` and `llm_model` are both passed. The
      report named the troubleshooting entry; the claim was actually in 8 places, including the
      frontmatter `description`, the format table and the performance notes, all corrected.
      Installing tesseract, which the skill told the reader to do, changes nothing.
      Also recorded: `exiftool_metadata()` returns `{}` unless an explicit `exiftool_path` is
      passed, so even the EXIF half is opt-in.
- [x] WRONG - `register_converter(".custom", conv)` as documented raises
      `TypeError: MarkItDown.register_converter() takes 2 positional arguments but 3 were given`.
      The real signature is `(converter, *, priority=0.0)`; the extension is decided by the
      converter's own `accepts()`.
- [x] WRONG - and this is the one that fails SILENTLY. The documented converter interface,
      `def convert(self, stream, file_extension)`, does not match what markitdown calls:
      `convert(self, file_stream, stream_info, **kwargs)` plus a REQUIRED
      `accepts(self, file_stream, stream_info, **kwargs) -> bool` that gates it. Registered and
      run verbatim, the documented converter never fires and `convert()` returns `'hello'` - the
      plain-text fallback - with no error raised. The corrected example, extracted back out of
      the file and executed, returns `'# Custom Format\n\nhello'`. Both methods are now shown,
      with the silent-failure mode stated.
- [x] WRONG - `convert_stream()` was shown taking `file_extension` positionally. It is
      keyword-only in the real signature; the prose now says so, and `stream_info` is documented
      beside it as the richer alternative.
- [x] WRONG - the Azure auth env var was documented as `AZURE_DOCUMENT_INTELLIGENCE_KEY` in two
      places. The code reads `AZURE_API_KEY`, falling back to `DefaultAzureCredential`.
- [x] DANGLING - the plugin-development pointer was the bare repo-relative path
      `packages/markitdown-sample-plugin`, which ships nowhere in this plugin and is not a URL, so
      it resolves to nothing from an install. Now the upstream URL.
- [x] UNEXECUTABLE - `docker build -t markitdown:latest .` had no stated precondition and no
      `Dockerfile` ships with the skill, so the command fails wherever a reader happens to stand.
      The clone step is now explicit.
- [x] STALE - the recommended vision model carried no date or version marker, so it reads as
      current forever. Now dated, and pointed at the live model list.
- [x] Every code block changed here was executed against the real library, not reviewed. The
      custom-converter block was extracted from the shipped file by fence-parsing and run, so what
      is asserted is the text a reader gets, not a retyped copy of it.
- [x] Description re-measured after the edit: 195 characters, under the 1024 cap. Derived
      artifacts regenerated (`skill_triggers.json`, `docs/skills.md`) because the frontmatter
      description changed.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] No session narrative or private provenance; no machine paths.
- [x] Typographic tell scan clean over every changed file, with an em-dash control proving the
      scanner reports a positive.

## Decision review, same date

- [x] The `OCR` trigger is RESTORED to the description, with the correction attached. Removing it
      made the description true and the skill unreachable for the exact query it now answers best:
      someone asking how to OCR a scanned document needs to arrive here and learn markitdown does
      not, and what to use instead. A description selects for TRIGGERS; the accuracy lives in the
      body, which states it in 8 places. The description now carries `OCR`, `tesseract` and
      `scanned` as matchable terms while saying plainly that no local OCR exists.
- [x] Description re-measured after the restore: 351 characters, well under the 1024 cap.
- [x] The restore was VERIFIED against the derived trigger artifact, not assumed. The first attempt
      put the OCR clause in a second sentence, where it reached the available-skills listing but
      NOT the per-prompt router: `build_skill_triggers.distill` drops tokens under 4 characters, so
      `ocr` can never be a trigger token at all, and `MAX_HEAD` caps the head at 14, which the
      format list already filled. The clause is now front-loaded so `scanned` and `tesseract` are
      real router tokens.
- [x] Trade recorded: the head holds 14 tokens, so admitting `scanned` and `tesseract` cost `epub`,
      `youtube` and `urls` their slots. They remain in the description TEXT, which is what the
      listing channel injects; only the router loses them. Accepted because an OCR-shaped query is
      a far more likely arrival path here than a YouTube one, and because a skill whose description
      the listing budget drops has the router as its only channel.
- [x] The reworded description first shipped a `: ` inside the plain scalar (`for LLM use: PDF`),
      which the repo-gate rejected: that is not valid YAML, and the regex front-matter readers
      recover the value anyway so nothing downstream would have noticed. Reworded with ` - ` and
      re-parsed with a real YAML loader, not a regex.
- [x] `pages` removed from the description. It was filler introduced by the phrase "scanned pages"
      and it occupied one of the 14 head slots, displacing `epub`; `scanned` alone carries the
      meaning. Measured before and after: the head now ends `... html, json, epub`.
