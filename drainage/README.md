# Drainage pit candidate, first reviewed fixture

`Read-PitFixture.ps1` prints JSON; optional `-OutputPath` creates a new file and
refuses overwrite. Source reports are hash-pinned and never edited. Run
`tests/Test-Pit.ps1` for offline checks.

This is a candidate assembler from explicitly reviewed fixture selections, not
pit discovery or automatic pump recognition. Handles, group assignments and
category declarations live in the fixture; no such constants are recognition rules.
Every member retains its raw record, layer, definition coordinates, source hash
and definition path. Geometry points supplement rather than replace raw DXF
(which retains radii, spline knots, closure, transforms and visibility).

K1-4 has four outer edges, one inner outline, one auxiliary polyline and two
separate pump-like groups. Category declarations are category-only candidates.
No actual power, duty/standby mode or model is assigned to an installed pump.

Placement remains unresolved and InstanceWCS is not_computed. The three reviewed
paths coexist. Equal top INSERT transforms do not establish view scope, evaluated
visibility, revision validity or permission to remove a duplicate. The index lacks
69F4 rotation/scale/normal. Independent export hashes do not establish database
revision correspondence, even if DWG paths and Handles match. Cross-document
coordinate matching is denied by the first-stage API. No circuits, connections
or quantity outputs exist. The earlier unknown-window record is retained separately.
