# Layout-aware reader (experimental)

`Read-DesignStatementsAuto.ps1 -ReportPath <snapshot> -Summary` uses layout mode.
`-LegacySpacing` reproduces the previous spacing-only baseline.
The module API accepts `-Geometry $snapshot.geometryRecords -LayoutAware`; old callers retain compatibility.

## Evidence pipeline

Read straight LINE and zero-bulge LWPOLYLINE WCS vertices, preserving raw records and snapshot identities. Long axis-aligned segments (relative to observed text pitch) become separator candidates. Closed four-edge rectangular polylines become frame candidates. Repeated horizontal spans intersecting at least two vertical spans become grid candidates. No rectangle proves a design region.

Paragraph and region joins are vetoed when their text-anchor segment crosses a supported separator. Existing numbering, indentation, gap and punctuation checks remain. Text columns expose text-anchor extents, not glyph bounds; dominant X, line pitch, rotation qualification and boundary source evidence are retained. Title-pattern and attached-attribute metadata regions are separate candidates. All attached ATTRIB are conservatively excluded from body. No engineering interpretation is assigned to geometry.

Rotation fields, when present, classify horizontal, vertical or other (one-degree tolerance). Missing rotation is **unknown**, retained in a provisional horizontal-layout interpretation with a snapshot coverage ReviewItem. The real report lacks rotation fields; real rotated-text isolation cannot be verified from this snapshot. Controlled tests verify the supplied-angle behavior. The extractor was not changed.

MTEXT preserves raw string and all recognized formatting tokens. Paragraph breaks and a small set of display directives yield a plain-text candidate. Braces, stacked text, fields and unrecognized escapes remain unresolved; MTEXT is not automatically admitted to paragraph parsing. All nine real records retain the original review obligation.

## Limits and audit

This is not complete sheet segmentation. Pitch still comes from the dominant observed spacing, not a robust mixed-scale estimator. Boundaries use XY projection; tilted/curved boundaries are unsupported. Titleblock internal geometry is not expanded. Standalone TEXT inside a titleblock cannot always be excluded without its boundary evidence. Attribute exclusion is deliberately conservative and may lose legitimate attributed body text. Text-column bounds are anchor extents only. Separator vetoes may over-split text and need review; lower review count is not an objective.

The controlled tests cover horizontal/vertical separation, intact multiline paragraphs, two columns, translation/scale/Handle perturbation, rotation, metadata exclusion and MTEXT preservation. Real tests preserve both known paragraph orders and print before/after metrics. Five additional paragraphs are sampled using seed 20260924; raw text chains are printed for inspection. This is not an accuracy estimate or a visual CAD validation.

Observed baseline: 105 regions / 369 paragraphs / 284 high orders / 242 reviews.
Layout mode: 141 regions / 368 paragraphs / 243 high orders / 319 reviews.
The extra reviews indicate unresolved boundary/coverage questions, not verified corrections.

No source snapshot is changed. No AutoCAD, external standards, circuits, routing or quantity operations are invoked.
