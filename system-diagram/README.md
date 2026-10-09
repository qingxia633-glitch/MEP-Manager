# System diagram candidate model v1

The [outgoing row layer](OutgoingRows.README.md) structures reviewed local rows
without creating circuits, terminal connections or quantities.

The separate [panel configuration evidence layer](PanelConfiguration.README.md)
adds scoped reviewed definitions and instance-to-configuration hypotheses without
changing this row model or resolving its existing power bindings.

Read-only composition of an explicitly selected local fixture. No discovery,
AutoCAD access, further block probing, Circuit, connections or quantities.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File system-diagram/tests/Test-Diagram.ps1
# Returns an object, writes no report:
$view = & ./system-diagram/Read-LocalFixture.ps1
$view | ConvertTo-Json -Depth 90
```

## Contracts

- `SystemDiagramLocalView`: scoped ID, immutable source SHA-256/path/DWG,
  drawing-unit coordinate context, separate evidence collections and limitations.
- `DiagramRowCandidate`: INSERT WCS baseline, raw basis, member references,
  statement candidates, spacing evidence, candidate/ambiguous status, conflicts,
  scoped human evidence. Caller supplies the local anchors. No row discovery claim.
- `StatementCandidate`: raw TEXT/ATTRIB, Handle and parent, layer, both reported
  points, coordinate status, lexical candidate kind and unbound/ambiguous status.
  Attribute points remain raw OCS; parent WCS is explicitly the layout reference.
  TEXT uses insertion, not guessed alignment mode. Text patterns give no final role.
- `AlignmentEvidence`: two references, point types, DX/DY, baseline relation,
  numeric tolerance, layout band and residual. Every matching band is retained;
  no nearest-row tie breaking. Bands and tolerances are drawing units.
- `DynamicBlockMetadataEvidence`: raw names, serialized values and allowed values,
  per-field read statuses and all raw property fields; no engineering interpretation.
- `DeviceCandidate`: instance path including each report hash, outer INSERT and
  child reference, transforms, four raw geometry members, attribute evidence,
  separate human confirmation, tentative semantic role and correspondence status.
  The role is supplied for this investigated fixture, not automatically classified.
  Definition ATTDEF and reference-attached ATTRIB have separate collections.
- `RepresentationEquivalence`: two raw representations, transformed endpoints,
  residual/tolerance, explicit style comparison, DXF60, source transform and scope.
  Matching geometry/style gives one group with two retained members. This is an
  equivalence group, not an output line or a quantity. No raw entity is deleted.

## Scope and evidence boundaries

Gold Handles and local choices are confined to `tests/local-fixture.json`.
Three reports are independently fingerprinted; same DWG/Handle does not merge
snapshots. The fixture records explicit, **candidate** report correspondences:
matching references do not prove no DWG edits occurred between exports.
Human symbol confirmation is attached only to R4 in this local snapshot/view.
The *U404 equivalence is separate definition evidence, not an extra Q1-Q5 row.

The equivalence implementation supports open straight two-vertex LWPOLYLINE,
XY normals and planar INSERT translation/rotation/scaling with definition base.
Other geometry is rejected. Style comparison conservatively requires unit scale
and equality of explicit layer/color/linetype/lineweight/width fields; it is not a
general effective CAD style evaluator. DXF60 is not evaluated dynamic visibility.
No cross-snapshot human-confirmation migration or full nested rendering occurs.

Future consumers must use instance path + source snapshot + equivalence scope;
they must not globally deduplicate by definition Handle, text, or geometry alone.
Electrical ownership, power allocation, ratings and actual connectivity remain
unresolved. Next validation should concern candidate row/statement roles, not
electrical routing or quantities.

## Validated fixture

Five candidate rows, 22 statements, five device candidates, five independent
dynamic metadata records and one separate *U404 definition equivalence group.
R3/R4 each keep two panel labels. All statement semantic bindings remain unbound.
The group retains both the hidden direct line and the child line; no line length
is accumulated. The fixture runner returns data without saving a result file.

106 checks cover real sources, duplicate labels, human evidence scoping, renamed
Handles, translated layout, overlapping row bands, absent row association, raw
dynamic values, separate attributes, JSON serialization, endpoint reversal,
changed geometry/style, unsupported bulges/variable widths and absent final
Circuit/quantity fields. Probe adapters copy CAD field values into plain data:
PowerShell provider metadata attached to raw input lines is not CAD evidence.

## Field roles and binding hypotheses

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File system-diagram/tests/Test-Fields.ps1
$fields = & ./system-diagram/Read-FieldFixture.ps1
```

`FieldCandidates.psm1` adds a derived layer without mutating the existing view,
Statements, raw reports or binding statuses:

- `ColumnPatternCandidate`: scoped snapshot, normalization basis, X/Y ranges,
  medians and full sample distributions, statement/row frequency, median-based
  horizontal order, per-variant distributions, support and exception samples.
  No fixed X-column test. Spread is preserved, not trimmed to fit a rule.
- `FieldRoleCandidate`: original statement reference, one or more lexical roles,
  scoped rule text, pattern references, layout offsets and point types,
  visibility evidence, candidate status and conflicts. Pattern summaries and
  lexical roles share observations; they are not independent confirmations.
- `BindingHypothesis`: power statement, row/individual identifier/group
  alternatives, supporting role references, opposing and missing evidence.
  Every hypothesis is unresolved; no selected or confirmed target exists.

The separate `tests/field-fixture.json` supplies the surveyed family, lexical
candidate patterns, descriptive variant conditions and observation windows.
These are project-local experimental vocabulary, not universal design rules.
The runner verifies the frozen report SHA-256, supports only the surveyed
unrotated unit-scale anchors and groups their X baselines for layout observation.
These groups are NOT confirmed drawing regions or engineering systems.

The output keeps the 34-row survey and original five-row view in separate
analysis scopes. The five rows are a subset, not five additional objects.
Pattern IDs/field IDs are result-scope local. Source statement references retain
snapshot, view, Handle, parent Handle and raw text; matching text is never merged.

Four candidate bands cover conductor expression, row identifier, identifier/load
expression and power expression. Five descriptive variants retain 13 single-QWB,
2 double-QWB, 8 WP, 6 WE and 5 JL rows. Missing kW means not observed in the
supplied window. Five hidden JLM attribute claims remain role candidates but
are exception samples and cannot support a visible identifier band or target.

`visibleFieldSupport` means eligible for candidate layout statistics, NOT proven
visible on screen. TEXT display state is not exported; ATTRIB DXF70 is preserved
as a flag. Both keep `renderedVisibility=not_verified`. ATTRIB alignment is used
only when its normal and justification establish a valid XY reference; other
attribute frames remain unsupported. Top-level TEXT uses reported insertion.

No cross-view reference is resolved, no power is assigned to a box, and no
Circuit, device connection, center path, quantity or new CAD acquisition occurs.

The field suite passes 58 checks: real variant counts, shifted power positions,
unresolved multi-target ownership, hidden-attribute exceptions, cross-view text,
multiple role candidates, unchanged input facts, JSON roundtrip, snapshot/view
scope rejection and competing-row ambiguity. Existing suites remain separate.
