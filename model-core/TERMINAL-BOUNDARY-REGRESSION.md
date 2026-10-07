# Terminal boundary gap refinement

This is a bounded validation sample, not a reusable terminal-mapping algorithm.

The manifest references the existing terminal-box probe by SHA-256 and raw
Handles. `Read-GapBoundaryFixture.ps1` resolves the closed, straight polyline
and POINT records and computes WCS from the verified top-level INSERT transform.
Unsupported normals or curved outlines are rejected. The two ATTDEF bounding-box
errors remain in the audit; their raw source records are preserved.

`GapBoundary.ps1` tests point-to-boundary distance with tolerance 0.00001 drawing
units. This is a numeric report comparison tolerance, not a connection tolerance.
It does not use the symbol bounding box as a substitute for the raw outline.
POINT hits, when present, still have unresolved meaning.

The existing NetworkGapCandidate now retains originalGapDistance, boundaryObjectRef,
left/rightRepresentationRef, left/rightBoundaryContact, boundaryRelationStatus,
and internalContinuityStatus. Left/right name the reviewed fixture sides, never
signal direction. A definition read does not authorize an internal edge.

For the three DZX gaps, both boundary contacts are supported and the reason is now
internal_terminal_mapping_not_represented; internal_continuity_not_represented
also remains open. Gap distances and open-end records are retained. The isolator
gap is unchanged. Boundary objects are represented by the existing
NetworkBoundaryCandidate separately in each system; no new node or edge is added.

Negative tests cover one-sided contact, synthetic POINT contact without terminal
identity, asserted contact across a declared gap, system isolation, unchanged
Requirements, and empty routing/physical/network/quantity outputs.

Capabilities boundary_object_relation and gap_semantic_refinement are
validated_sample for this fixture only. They are not reusable.

Run the local suite with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File model-core/tests/Test-LocalLogicalNetwork.ps1
```

Run all offline suites with `model-core/tests/Run-Regressions.ps1` using the same
PowerShell options. No AutoCAD invocation is required.
