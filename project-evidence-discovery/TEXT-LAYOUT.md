# Text Layout Evidence Plumbing v0.1

Contract: read existing TEXT/MTEXT/attached ATTRIB layout fields into annotation
evidence. Exporter stays 2.5; reports without layout fields stay readable. No note
classification, scope inference, admission change or new CAD acquisition.

Invariants: preserve owner-qualified identity, serialized text, reported values,
statuses and provenance. Coordinates used as WCS require valid finite triples and
WCS evidence. Legacy ATTRIB DXF10 is retained as raw OCS, never relabeled WCS.
MTEXT direction is not TEXT rotation. Bbox is never synthesized from insertion.

Failure: missing/failed/unknown status or frame never produces valid WCS bounds.
Malformed read values become invalid_result; original reported status/value remain
in layout_evidence.fields. Failed current conversion never falls back to raw DXF.
Legacy explicit Insertion_WCS remains usable with legacy status recorded separately.

Acceptance/adversarial matrix: TEXT round-trip; MTEXT direction/no fake rotation;
ATTRIB WCS preference/owner identity/tag/visibility; missing/error/reversed/NaN bbox;
foreign frame; legacy OCS; failed conversion; no proximity binding or scope approval.
Validate two verified real reports, existing layout tests, current Discovery tests,
registered legacy failures, Runner tests/three real cases, Test 15 and frozen hashes.

Structured scalar values have sibling `<name>_status`. Bounds contain min_wcs,
max_wcs, frame, status and reported_status. `layout_evidence.fields` preserves raw
serialized values and reported statuses; `position_source` distinguishes
exporter_wcs, legacy_exporter_wcs, legacy_raw_dxf and missing. Legacy raw DXF has
position_status=unresolved and position_wcs=null. Visibility is raw evidence, not
final visible-state resolution. No paragraph/table/Field/nested/Layout/Xref support.
