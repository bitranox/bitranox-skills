# checklist - an output-identity claim across the caller's settings

One queued contribution: a bullet in "Validating a claim or comparing before/after" saying an
"output byte-identical" claim is proven only by hashing old and new output with each
caller-visible setting of the output object flipped (Rich `Console`: `highlight`, `color_system`,
widths), with the measured miss.

Decisions: d-20261120-4ee827cf

## RED

- [x] Skill decisions read first: none rejected or removed.
- [x] Text check of the pre-edit file: the only "byte-identical" was the one-slot cache paragraph,
      with no word on varying the output object's settings; `highlight=True` 0 hits.

## GREEN

- [x] Quote-back probe (opus, haiku): P1 answered "not proven" with a quote of the new bullet.

## REFACTOR

- [x] Closed (opus): "cross product" versus "each default flipped once" read as two standards;
      now one rule (flip each setting, the full product only when there are few).
- [x] Declined (opus, haiku): a fixed width count and the full Console parameter list - the
      bullet tells the reader to list the parameters of the object in front of them.
- [x] Width, fence and ASCII checks on the added lines clean.
