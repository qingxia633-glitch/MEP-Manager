# Local geometry units — phase 1

This is the independent local unit-recognition entry point. It does not import
`prototype/Discover.psm1`, enumerate `Walk-Contour` paths, search a whole drawing,
classify tray systems, associate annotations, read colors, or generate center paths.
The existing prototype scripts, tests and results remain historical experiments.
No existing entry point has been deleted or rewritten.

## Run

From the repository root, with Windows PowerShell 5.1 and its built-in C# compiler:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File geometry-units/tests/Test-Units.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File geometry-units/Run-Units.ps1 -Report local_test_data/MEP-entity-report.txt -Selection geometry-units/tests/real-sample.json -Output local_test_data/geometry-units-result.json
```

Omit `-Output` to print JSON without writing a result. The explicit selection file
is a local input fixture, not a search rule. The runner reads only `selectionHandles`;
expected unit memberships are read only by tests. Use a fresh PowerShell process
after changing the C# source, because compiled types remain loaded in a process.

## Pipeline and data contract

1. `Read-LocalEntities` extracts the caller-selected records without changing the
   report. RawEntity retains Handle, snapshot hash, drawing, report line, original
   record, XYZ coordinates, bulges, layer, closure and missing-color status.
2. `Get-LocalTrayUnits` validates finite, nondegenerate, straight, coplanar XY input.
   The C# recognizer receives only identities and geometry, not layer semantics,
   widths, expected answers or report-specific coordinates.
3. Whole-segment equivalence is checked in both directions. GeometryEdge retains
   every `sourceHandle`, source direction, segment index and measured residual.
   Exact exported-coordinate duplicates and within-tolerance duplicates have
   different statuses. Original entities are never removed or edited.
4. Pairwise-compatible endpoint clusters form a planar embedding. Interior
   crossings and partial overlaps are rejected, not silently connected or split.
   Nontransitive tolerance clusters are rejected rather than joined by chaining.
5. Angularly ordered directed edges enumerate bounded faces. This is face traversal,
   not the old bounded path enumeration. Exterior and zero-area dangling walks do
   not become closed units. Non-simple bounded walks remain unresolved.
6. Rectangular faces are straight hypotheses. Two unused parallel sides extending
   outside a face across a perpendicular boundary edge form a partial straight
   hypothesis. Its remote closure is `unknown_far_end`; no edge is fabricated.
   Competing side assignments remain unresolved.
7. Two incident units establish a shared-edge Interface regardless of duplicate
   count. A nonrectangular bounded unit with two nonparallel equal-width interfaces
   is a bend hypothesis. Edge count and turn angle are not prescribed. Other
   shapes remain `unknown`, rather than being forced into a bend template.

The JSON contains `rawEntities`, `geometryEdges`, `contours`, `units`, `interfaces`,
`unassignedEdgeIds`, `diagnostics` and explicit limitations. Units reference contours;
contours list ordered boundary edges and vertices. Closed contours implicitly join
the last vertex to the first; partial contours do not. Snap residuals are preserved.
Unit sourceHandles are the union of all boundary-edge sources, so a shared edge's
two copies appear in both incident units. This records provenance, not original
authoring ownership. G/C/U/I identifiers are local result IDs, not permanent CAD IDs.

All dimensions remain in drawing units. Straight width is supported by its transverse
interface; a bend retains the two interface widths rather than asserting one global
clearance width. Results are geometric hypotheses, not semantic confirmation that
every rectangular or bent polygon in an arbitrary drawing is a tray.

## Verified real sample

| Result | Observation |
|---|---|
| Raw entities | 14 retained |
| Geometry edges | 12, including two two-source groups |
| G3 / I1 | sources 52CE9 and 52904; connects U3 to U1 |
| G9 / I2 | sources 52908 and 52901; connects U1 to U2 |
| U3 / C3 | partial straight, width 200, remote closure unknown |
| U1 / C1 | closed seven-sided bend, two interfaces |
| U2 / C2 | closed straight, width 200 |
| Unassigned edges | 0 |
| Center paths | not generated |

The resulting unit adjacency is U3 — I1 — U1 — I2 — U2. Neither duplicate count nor
individual decorative boundary vertices add an engineering branch. Sample Handles
and expected values belong only to this documentation and the test fixture.

## Validation and limits

Tests cover real memberships and provenance (not just counts), all individual edge
reversals, renamed Handles/layers, translation, rotation, uniform width scaling,
independent strip-width change, same/opposite duplicate directions, removal of each
copy and one copy from both groups, JSON round trips, tolerance residuals and a
separate six-sided non-right-angle elbow. Negative cases cover arcs, closed input
polylines, elevations, duplicate identities, interior crossings and partial overlap.

Current deliberate limits:

- Caller-supplied small local input; no whole-drawing candidate discovery.
- Straight two-vertex LINE/open zero-bulge LWPOLYLINE only; one shared XY plane.
- No splitting at partial overlaps, interior crossings or T contacts inside edges.
- Partial straight reconstruction requires one observed segment per side plus an
  interface to a bounded face. General broken side chains and missing interface
  edges remain outside phase 1.
- Bounded faces can be unknown shapes. General T/cross/variable-width fittings and
  competing decompositions are not fully classified.
- No assumption that an observed end is the end of the entire tray system.
- Pairwise geometry checks are quadratic, intended for the small local scope.

Keep the old tests and data. `prototype/Test-Discovery.ps1` writes its historical
JSON result; preserve or restore that file when rerunning the old test for regression.
