# Fire alarm 2D routing evidence (experimental)

`RoutingGeometry.cs` builds a straight-segment graph; `Read-AlarmRouting.ps1` is the
snapshot-scoped adapter. Input snapshot and reviewed polygon/logical artifacts are
SHA-256 pinned. Raw entities and previous requirements are never modified.

## Scope and admission

- The existing fire fixture supplies the drawing-specific `WIRE-消防` **candidate**
  layer clue. This does not establish a real loop or electrical membership.
- Phone, control/unknown and other layers are excluded, not inferred from proximity.
- All 52 projected polygon vertices are used for finite-segment clipping. No second
  page translation is applied. Clipped endpoints do not create crossing connections.
- Each output edge retains its raw entity reference and original segment index.
  Source geometry records retain the original vertex pairs, independently of clipping.
- LINE and straight LWPOLYLINE are supported. Nonzero bulges or missing vertices
  are quarantined, never replaced by bounding-box diagonals or arc chords.
- Units are the snapshot's drawing units (`INSUNITS=0` in this fixture); no metre
  conversion, installation heights, allowances, quantities or formal circuits.

## Topology

Finite endpoint contacts and T junctions connect. T junctions split an actual
segment while conserving length. Interior crossings do not split or connect.
Z disagreement does not connect in the XY graph. Tolerance is 0.001 drawing units.
Near open ends within an explicit 1-unit investigation radius become unresolved
gap candidates and **never** edges. This radius is not a claim of exhaustive gap
discovery. Longer unexplained breaks remain open endpoints.

Device endpoint relations remain unresolved until real plan-instance symbol
boundaries and their transforms are admitted. INSERT points are not ports.
This implementation deliberately does not infer device boundaries from system
diagram probes or identically named blocks in another drawing.

The system diagram's 2 gaps and 17 open ends remain separately source-scoped in
the result. In particular DZX has `bridgeAllowed=false`; it is not projected into
this plan or silently converted into internal continuity.

Logical edges only produce comparison reviews. No logical relation generates a
geometric segment. All upstream review items remain open, including quantity
mismatches. Connected components are geometric candidates, not circuits.

## Golden selection and limitations

Select the component with most real edges, then fewest open ends, then stable ID.
All admitted line scopes currently have the same candidate strength, and all
device endpoint bindings are unresolved; no stronger endpoint sample is claimed.
The selected sample is therefore a geometry golden only, not a device-to-device
route. Graph fragmentation is retained rather than repaired to fit logical goals.

Run `model-core/tests/Test-AlarmRouting.ps1`; optional `-OutputPath` exports the
complete auditable graph. `model-core/tests/Run-Regressions.ps1` includes it.
