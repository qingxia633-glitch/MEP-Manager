# Local project/view loop

Scope: explicitly selected, manually reviewed local sample; no region discovery,
whole-drawing segmentation, system model, center path or quantity calculation.

## Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File view-context/tests/Test-Context.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File view-context/Run-LocalView.ps1 -Report local_test_data/MEP-entity-report.txt -ContextSpec view-context/tests/confirmed-local.json -Output local_test_data/local-view-result.json
```

The context fixture pins the reviewed snapshot, selected geometry and annotation
identities, and human claims. Those answers are not in generic algorithms. A changed
snapshot requires new review; the runner refuses to reuse the fixture automatically.
Project/document IDs in the fixture are local registration IDs, not inferred project
metadata. DrawingSet completeness is `unknown` (or explicitly `incomplete`), never
inferred complete from a single registered file.

## Data

- `context`: ProjectContext, DrawingSet, DrawingDocumentRef, DrawingSnapshotRef,
  DrawingRegion, ViewContext and CoordinateContext represented by named records.
- `contextRefs`: project, set/set-snapshot, document/drawing-snapshot, region, view,
  coordinate context and unique analysis-run IDs. Local U/G/E IDs are scoped by run.
- `geometry`: deep-copy adapter over unchanged phase-1 output, plus context refs and
  width measurements. Original RawEntity coordinates and report fingerprints remain.
- `evidence`: existing fact/claim records, separate spatial/association statuses, and
  appended HumanConfirmation. Automatic status remains visible after confirmation.
- `widthMeasurements`: source edge pair, drawing spacing, method, overlap, residual,
  tolerance, coordinate context, dependencies and optional independently calibrated
  engineering value. No Interface is required for a closed rectangular straight.
- `measurementEligibility`: subject/run, view, quantity kind, status, reasons,
  missing prerequisites and evidence references. No quantity value is emitted.

Only the declared exact geometry set receives the human view confirmation. Snapshot,
region, view, project, drawing-set snapshot, building, storey and view declaration
must match the confirmation. Marker/text confirmation additionally requires the
automatic unique association and the confirmed text values. Ambiguity is never
resolved merely by copying a confirmation to another scope. Unselected annotation
Handles are reported separately rather than receiving local context.

Full region boundaries, axis grid, building elevation and unit calibration remain
unknown. A plotted `1:50` or `1:100` declaration never transforms raw coordinates.
Optional engineering conversion requires an explicitly confirmed independent factor,
evidence refs and matching coordinate/region/view/drawing-snapshot scope. Unsupported
scale declarations are retained but do not produce an engineering value.

## Spatial relations and compatibility

`Get-UnitSpatialRelations` validates finite XYZ and simple coplanar closed polygons.
It checks vertex tolerance first, then observed edges, then ray-crossing interior.
Outside is emitted only for a valid closed contour in the same plane. Open contours
may have observed vertex/boundary hits but cannot assert interior or outside. Invalid
polygons, noncoplanar points and holes currently produce unknown.

Associations have `spatialRelations[]` per unit and an aggregate `spatialRelation`.
Ownership is separately `supported`, `ambiguous`, `insufficient`, or (in the scoped
adapter) `human_confirmed`. Multiple interior targets remain ambiguous. The old
`status` field is retained for successful/ambiguous callers, but the misleading
`outside_supplied_units` label is removed. No nearest-contour ownership rule is used.

Broad `electric power` and one strong-power subtype are recorded as compatible
broad/specific claims, not a string-inequality conflict. Security versus strong-power
and competing strong-power types retain the old explicit conflicts. Other unknown
type relationships remain unresolved; no comprehensive ontology is claimed.

## Eligibility limits

Known plan views are conditional until scale, drawing-set completeness and measurement
policy/duplicate-expression review are available. Unverified/unknown views remain
unresolved. Legend and detail CAD sketches are excluded for `installed_plan_length`.
That exclusion does not prohibit explicit detail dimensions from supporting a future
different task. The schema admits `eligible`, but this minimal stage never grants
unconditional final quantity eligibility.

Width extraction currently uses the longer opposing edges of a closed straight
rectangle; it is a geometric width candidate, not a universal installation-direction
rule. Square axes remain ambiguous. Broken side chains, polygon holes, view discovery,
cross-DWG inference, engineering elevation and quantities are outside this stage.
