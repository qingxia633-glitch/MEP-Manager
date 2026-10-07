# TEXT bbox paragraph continuity (experimental)

Layout mode only; LegacySpacing and downstream statement semantics are unchanged. Only top-level TEXT with a valid positive WCS bbox marked `read` is eligible. MTEXT and ATTRIB retain their existing treatment. Raw text, Handle, rotation and source snapshots are never rewritten.

## Decisions

The old insertion-X corridor remains the fallback. A bbox-overlapping line outside that corridor is considered, but can join only with compatible vertical spacing, overlapping horizontal ranges of the start/previous text and next text, comparable text height, unfinished punctuation, lexical continuation, no independent section number, no title cue and no separator crossing. Ratios are relative to observed pitch/text size, not project coordinates or identifiers.

Geometry separation is checked on both insertion-point and bbox-center transitions. Explicit boundary crossings reject joining. Large-font/title candidates stop existing-corridor continuation conservatively. A close or overlapping bbox alone does not create membership. The column envelope is a provisional start/previous-line envelope, not a recovered full-page column model.

`ContinuationEvidence` preserves source pairs, bbox availability, X bounds/overlap ratios, horizontal gap, indentation, spacing, punctuation, lexical cue, font compatibility, separator result, numbering and decision. Accepted bbox extensions produce `bbox_continuity_candidate` ReviewItems rather than silently becoming confirmed reading order. Column candidates expose bbox extents and these pairwise evidence records while retaining anchor bounds separately.

Unavailable, missing, malformed or wrong-frame bbox data does not delete or invalidate an entity; it selects the old position/spacing/numbering/separator path. The current text eligibility rules still apply, so empty text is not body content.

## Validation

`tests/Test-BBoxContinuity.ps1` first reproduced the real indented-line omission before the fix. It verifies recovery, existing golden orders, independent-number stopping, horizontal/vertical boundaries, title/attribute/large-font rejection, overlap-only and punctuation counterexamples, missing-bbox fallback, and transformed controlled input. `-ControlledOnly` runs the small cases.

`tests/Compare-BBoxContinuity.ps1` runs B1/B2 using the same current reader, prints metrics, all changed member lists and up to ten changed paragraphs sampled without replacement with seed 20260924. It reports the non-target count separately: the known repair target is not a blind sample. Output is stdout only. Changes need qualitative review; its lists are not accuracy labels. Rejected bbox-only candidates cannot replace existing end-boundary evidence.

## Limits

This remains an experimental, near-horizontal reader with a global dominant pitch. Short fragments excluded by the existing body filter, incomplete geometry boundaries, unusual typography, nested text and more complex list/column layouts remain unresolved. Restoring one continuation does not prove an entire numbered section complete. No AutoCAD, circuits, physical paths, quantities or new semantic types are involved.
