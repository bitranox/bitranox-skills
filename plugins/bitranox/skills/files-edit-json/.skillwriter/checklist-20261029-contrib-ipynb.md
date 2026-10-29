# skill-writer checklist - files-edit-json (Jupyter notebooks)

- [x] Change: SKILL.md gains "Jupyter notebooks (.ipynb) are JSON: edit them without nbformat"
      (byte-identity check before writing, select the cell by id, keep the source type); the
      description names "a Jupyter notebook (.ipynb)".
- [x] RED (text check): `grep -niE 'ipynb|nbformat|notebook' SKILL.md` exited 1.
- [x] Run on nbformat 5.11.1: a notebook whose cell sources are single strings, read and written
      with `nbformat.read`/`nbformat.write`, comes back with every source as a list of lines (not
      identical); `json.dumps(nb, indent=1, ensure_ascii=False)` reproduces it byte for byte; a
      file nbformat itself wrote is reproduced by `indent=1, sort_keys=True, ensure_ascii=False`
      plus a trailing newline.
- [x] The section's code block executed on a copy: the diff shows the one changed source line.
- [x] GREEN quote-back: "first prove that a plain dump reproduces the file byte for byte ... and
      refuse to write when none do".
- [x] Description measured with len(): 314 characters, trigger-only.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
