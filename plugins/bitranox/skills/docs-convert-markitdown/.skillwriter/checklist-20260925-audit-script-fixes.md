# skill-writer checklist - docs-convert-markitdown (2026-09-25, skill-script audit fixes)

Scope: two factual corrections to the skill text, plus behaviour changes in the three bundled
scripts that the SKILL.md routing row names. The frontmatter `description` is unchanged, so no
routing keyword moved and no derived artifact needs regenerating.

Why a behavioural RED does not apply here: these are FACTUAL corrections to a reference skill that
is installed on this machine, so a subagent would answer from the installed wording rather than the
file under test. The evidence is the library source and executed runs instead, and the text check
below is run against the skill FILES.

- [x] WRONG - `references/file_formats.md` still told the reader to install tesseract for scanned
      PDFs and text-heavy images, in five places, contradicting the SKILL.md description and the
      same file's own PDF capability line. A recursive grep of the installed markitdown 0.1.8 for
      `tesseract|pytesseract|ocr` matches only `converters/_doc_intel_converter.py`, the REMOTE Azure
      Document Intelligence converter: there is no local OCR path. All five now say so and name
      the working routes (an `llm_client` for images, Azure Document Intelligence for PDFs).
- [x] WRONG - SKILL.md "Scanned documents" offered `llm_client` as an alternative for any scanned
      document. markitdown sends only image files (`.png`, `.jpg`, `.jpeg`) and PPTX pictures to the
      LLM (`ACCEPTED_FILE_EXTENSIONS` of `ImageConverter` and `PptxConverter`); a PDF with an
      embedded image and a working client produced zero LLM calls. The bullet now scopes
      `llm_client` to images and PPTX and sends scanned PDFs to Azure Document Intelligence.
- [x] Text check against the files: an install-tesseract / "ensure OCR" pattern matched 6 lines in
      the previous `file_formats.md` and matches none after the edit; the remaining `tesseract`
      mentions all state that installing it changes nothing.
- [x] Script behaviour the skill routes to, verified by the scripts' own test suites (subprocess
      runs against offline markitdown/openai stand-ins, plus real-library runs on generated HTML,
      PDF and PPTX fixtures): `batch_convert.py` mirrors subdirectories and exits 0/1/2;
      `convert_literature.py` likewise, with working INDEX links; `convert_with_ai.py` refuses
      inputs markitdown never describes and fails when an image description call fails. The
      routing row names the scripts only, so no SKILL.md line states a behaviour that changed.
- [x] Description unchanged (measured: not in the diff).
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] No session narrative or private provenance; no machine paths or addresses added.
- [x] Typographic tell scan clean over both changed files, with an em-dash control proving the
      scanner reports a positive.
