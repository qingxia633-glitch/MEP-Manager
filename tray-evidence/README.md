# Local tray evidence — phase 2

Independent evidence layer over the phase-1 JSON. It does not modify phase-1 objects,
DWG, AutoLISP or the legacy prototype. No center paths, quantities, color extraction,
whole-drawing tray search or category propagation are performed.

## Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tray-evidence/tests/Test-Evidence.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File tray-evidence/Run-Evidence.ps1 -Report local_test_data/MEP-entity-report.txt -GeometryResult local_test_data/geometry-units-result.json -UnitContext tray-evidence/tests/width-derived-units.json -Output local_test_data/tray-evidence-result.json
```

Omit `-Output` to print JSON. Omit `-UnitContext` to leave dimensional comparisons
`units_unresolved`. The example context preserves the prior *width-derived* scale;
its agreement is `consistent_not_independent`, not an independent measurement check.
Never mark that context independent merely to obtain a stronger result. Independent
calibration is used only in synthetic comparison tests.

The runner verifies the geometry/report SHA-256 match. `Read-AnnotationRegion` reads
TEXT, LINE, LWPOLYLINE and CIRCLE records whose bounding boxes intersect the supplied
unit extent expanded by explicit `-Margin` (default 6000 drawing units). Full selected
records are retained. This is report extraction around known units, not an automatic
whole-drawing tray search. Nested blocks/XREFs are not expanded.

## Association method

For each eligible open straight leader or polyline, examine both terminal directions:

1. Text alignment must project to the free end of the terminal baseline; its insertion
   point must project within the baseline span and within the configured text offset.
2. Match a circle center to the other terminal point within an explicit tolerance.
3. Classify the landing against each supplied contour: vertex, boundary, strict
   interior, outside, or unknown. Interior requires a valid simple closed XY polygon.
   Retain GeometryEdge hits and incident interfaces separately.
4. Retain layout residuals, circle gap, all Handles, per-unit spatial relations and
   the separate association status. Overlapping target units remain ambiguous.

No nearest-text ownership rule or Handle/layer-name filter is used. Text records are
parsed independently into identity, type phrase, width, height and installation.
Common dimension separators are recognized and original text is always retained.
Type phrases are clues rather than authoritative mappings from layer names.

A unique marked relation is `strong_spatial`. Without a circle, a still-valid terminal
landing is `reduced_no_marker`. Multiple matching leaders or targets stay ambiguous
and do not become unit facts. Text without a valid leader relation remains an unbound
weak candidate. Associations outside supplied units retain observed external landing
Handles, but do not create external TrayUnits or attach their claims to local units.

## Output and evidence policy

- `rawAnnotationRecords`: original report text, layer, location, hash and line number.
- `geometrySourceRefs`: references to unchanged phase-1 source entities.
- `associations`: text/leader/marker/landing chain and target candidates.
  `spatialRelation` describes geometry; `associationStatus` describes ownership.
  The legacy `status` field remains for compatibility; unsupported geometry is
  `unknown`, never evidence that the landing is outside.
- `weakCandidates`: unbound parsed tray text.
- `evidence`: separate geometry, color missingness, layer, annotation and width checks.
- `conflicts`: unresolved competing type, width, height or installation claims.
- `unitAssessments`: identity support, unresolved type claims, measured width,
  annotation-only height, installation statements and missing color status.

Evidence refers back to source Handles and associations. A conflicting type never
rejects tray identity. Layer, geometry and text values are not overwritten. Width
comparison carries scale provenance and independence explicitly. Planar width never
verifies height. Unit IDs are inherited from phase 1, not fixed identifiers in rules.
Broad and specific compatible type clues (such as power and residential strong
power) are retained together; string inequality alone does not prove conflict.
The optional `view-context` adapter adds scoped context and independent width
measurements without changing the original phase-1 width or raw coordinates.

For the real fixture, two ordinary-power annotation groups land on the bend and the
partial horizontal straight. Each has a type conflict with the security layer clue.
The vertical straight retains geometry/layer evidence only: adjacent-unit attributes
are not propagated in this stage. The nearby fire annotation lands on external fire
geometry, so it is excluded from local unit claims.

## Current limits

- Layout support is for TEXT with exported insertion/alignment points and straight
  terminal baselines; text height/rotation/bounding box are absent from the report.
- Native leaders, MTEXT formatting, arrows, branching leader networks and nested
  annotation blocks are not interpreted in this phase.
- Marker/text-offset thresholds are explicit drawing-unit parameters, not calibrated
  engineering dimensions; other annotation styles may remain unassociated.
- Text rows are grouped through a shared baseline, not by native CAD association.
- Generic dimension parsing assumes width-by-height for tray phrases; unusual
  multi-dimension syntax and ambiguous installation scope require review.
- No automatic inference of a scale, authoritative tray category or network-wide scope.
- Color is explicitly `not_exported` throughout.
- Interior testing does not support holes; invalid, noncoplanar or unsupported
  contours remain unknown. Open contours cannot provide interior evidence.

PowerShell files containing Chinese are UTF-8 with BOM for Windows PowerShell 5.1.
