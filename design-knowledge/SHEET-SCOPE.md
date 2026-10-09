# Sheet / Page Scope Resolver (experimental)

This is a separate spatial overlay. It does not edit RawEntity, ParagraphCandidate,
ReadingOrderCandidate, SectionCandidate, or design statements. No AutoCAD is invoked.

## Run

```powershell
$result = ./design-knowledge/Read-SheetScope.ps1 -ManifestPath ./design-knowledge/tests/sheet-scope-sample.json
$result.sheetSummary | Sort-Object number | Format-Table
```

The entry point returns an object and writes no report. The manifest pins each input
SHA-256 and explicitly supplies the correspondence between independently acquired
snapshots/probes. Matching DWG filenames or Handles alone does not migrate evidence.
The legend region in this manifest is a reviewed fixture, not automatic legend discovery.

## Geometry and identities

* Read direct probe entities and resolved parent paths. Find a closed straight convex
  polyline that contains a distinct closed inner polygon. Retain the supporting paths.
* Only supplied, not-DXF60-hidden child representations participate. DXF60 is evidence,
  not a general evaluator of AutoCAD dynamic visibility. Competing paths remain unresolved.
* Subtract each referenced block's base point, apply XYZ scale and rotation, convert
  through the normal's OCS basis, and apply insertion. Compose child and top-level
  transforms. Never use the anonymous block's whole-definition bounds or paper names.
* Tilted/non-horizontal and degenerate frame polygons are not admitted to XY containment.
* Pair title INSERTs by a title/number attribute bundle, attribute extents and INSERT
  containment. Multiple matching frames or titles produce review; no nearest or fixed
  offset fallback. Attribute fields and all source Handles remain available.

## Spatial overlay

`SheetCandidate`, `SheetFrameCandidate`, `TitleBlockCandidate`,
`DrawingIdentityCandidate`, `ColumnScopeCandidate`, and
`RegionToSheetAssociationCandidate` are candidate records, not engineering objects.

TEXT/MTEXT/attached ATTRIB extents are tested against true polygons. Boundary contact
is reviewed. Multiple pages are ambiguous. Missing bbox uses insertion evidence and
can reach only partial. Missing all geometry is unresolved, not outside. No largest
overlap allocation is performed. A region references all original fragments; it does
not silently discard out-of-page members or split/merge original paragraphs.

Columns are the existing reader's column segments scoped independently to a uniquely
supported page; segments are ordered horizontally and each retains its internal reading
order and separator evidence. They are not claimed to be a complete census of physical
columns. No cross-column continuation or page-based semantic inheritance is performed.

`regionCount` includes supported DesignTextRegionCandidate, SectionCandidate and supplied
LegendRegion associations, so those overlapping conceptual levels are not unique text counts.
`textAssociations` separately preserves each source text record.

## Coverage and review

Frame overlap is a polygon test. Frame-spacing review uses the nearest axis-aligned-bounds
gap relative to the frame's own short side: it is a diagnostic clue, not a drawing standard
or a proof that all whitespace is intentional. Unpaired titles, missing titles, duplicate
drawing numbers, crossing text and unsupported regions remain review items.

The cover is excluded. Unknown blocks are not recursively opened. Output has empty
`designStatements`, `circuits`, and `quantities`. Upstream reader semantics remain upstream.

## Tests

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-SheetScope.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Run-Regressions.ps1
```

The fixture's Handles, filenames and expected identities occur only in test/manifest
data, not in geometry or association decisions. Controlled tests also exercise renamed
blocks, a nonzero base point, nonuniform scale, rotation, reversed normal, unavailable
extents, cross-page boxes, missing titles, hidden representations and open frames.
