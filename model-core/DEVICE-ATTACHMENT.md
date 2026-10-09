# Device representation geometry and routing endpoint admission

Experimental, scoped to two reviewed static definitions in the existing fire alarm
plan and the compartment-one membership candidates. No role, raw entity, original
routing edge/component, requirement or quantity is modified.

## Inputs and provenance

`tests/device-representation-fixture.json` pins two real probes and explicitly
lists an ordered closed chain of real LINE handles for each boundary. The generic
geometry implementation contains no block names or handles. This is a reviewed
boundary adapter, **not automatic boundary recognition for arbitrary symbols**.
Each link and closure is validated from raw DXF coordinates. The overlapping
polylines and other symbol details remain separately recorded; neither a bbox nor
a guessed radius defines the boundary. Stroke widths are not expanded into a
physical envelope. Both probes' two ATTDEF BoundsError records remain diagnostics;
the selected boundary geometry itself has readable raw coordinates.

Existing routing and logical artifacts are pinned. The logical membership input
limits the batch to compartment-one smoke and ordinary sound-light candidates:
20 explicit smoke, 88 inherited smoke, 10 admitted ordinary sound-light expressions.
Cross-DWG same-name blocks are not accepted: probe DWG must exactly match snapshot.

## Transform

`DeviceRepresentation.cs` applies block-base subtraction, signed XYZ scale,
rotation in radians, the normal's arbitrary-axis basis, then WCS insertion.
Incomplete/degenerate transforms, dynamic state and nested/array instances are
blocked rather than guessed. Negative scale is preserved. Curves retain an affine
parametric basis; they are not discretized into fictitious boundary lines.
POINTs are transformed reference points with unresolved candidate-port semantics.

## Relations

The finite segment is checked against the actual transformed closed ring.
Endpoint-on-boundary and endpoint-inside support representation attachment only.
Pure crossing, near-only and no-relation never attach. Noncoplanar relevant pairs
remain unresolved; no height or Z correction is introduced. Tolerance is 0.001 and
near-only investigation radius is 1, both in original drawing units.
The `distance` field is the minimum endpoint-to-boundary distance, or zero for a
detected boundary intersection; it is not a general whole-segment proximity metric.

Pair statistics and per-instance strongest-relation summaries are separate.
An instance can have multiple edge relations. Golden samples are selected by
endpoint evidence, then crossing, then distance and stable source references.
Batch does not choose instances to obtain any target count.

`componentAttachments` is a separate overlay referencing immutable component IDs.
It never merges components, adds an edge through a device, assigns direction or
confirms ports/physical connections. `physicalConnections` and `confirmedPorts`
remain empty. Existing no-height/no-quantity boundaries remain in force.

Run `model-core/tests/Test-DeviceAttachment.ps1`; optional `-OutputPath` saves the
audit. Tests cover rotation, scaling, mirroring, base point, normal, incomplete
transforms, dynamic/nested blocks, near-only, crossing and real fixtures.
