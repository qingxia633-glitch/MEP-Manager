# TABLE Cell Evidence v0.1

## Contract

Report exporter 2.6-table-cell-evidence-v1 adds TableEvidenceVersion=1 to
top-level ModelSpace ACAD_TABLE objects. Every getter records Value/Status/Source
independently. TABLE identity and raw DXF remain available. Adapter returns a
separate table_evidence collection; cells never enter annotation/binding loops.

Identity: project, drawing, snapshot hash, full parent_path, table handle, space;
cell identity adds zero-based row_index and column_index. Merge aliases retain
master identity and raw observed contents, not independent facts. No cell is an
approved engineering fact, including unmerged cells.

## Invariants / failures

Old reports have missing cell evidence and no manufactured cells. Explicit empty
getter evidence differs from absent/error/unsupported content. Invalid indices,
duplicate identities, incomplete cell grids and invalid merge ranges fail closed.
Unknown merge/content/field details remain unresolved. GetText is preserved as
observed API content, never a promise of static text or full Field provenance.
Block references are not expanded. Multiple-content enumeration is unsupported
in this first ActiveX acquisition contract; no invented content_index.

Only ModelSpace top-level is supported. No TABLE header/row/system interpretation,
nearby-object binding, scope, propagation, Gate or quantity processing.

## Acceptance

Independent synthetic adapter cases cover identity, dimensions, Chinese strings,
empty/missing/error, merges, block/field, malformed/duplicate indices and negative
semantic/binding checks. Existing MTEXT/layout/current Discovery, legacy ledger,
Batch and Test 15 remain independent regressions. Real CAD support is distinct
from software support; current Core Console lacks ActiveX and requires manual-host
acquisition in full AutoCAD. Synthetic reports do not establish real CAD support.

## Getter basis

Autodesk ActiveX Table API: Rows, Columns, GetCellType, GetContentType, GetText,
IsEmpty, GetFieldId, GetBlockTableRecordId, IsMergedCell, GetCellTextStyle,
GetCellTextHeight and GetCellAlignment. Getter failures are preserved.

Reference: https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-ActiveX-Reference/files/GUID-7B82400C-53D0-4D1A-94FA-66BB3040F0AA.htm

Acquisition limits: multiple contents, formula internals, field dependencies,
cell geometric extents and master display-source semantics remain unresolved.
Table bounds/insertion/style and row heights/column widths are best-effort metadata.

### Cell.Empty VARIANT_BOOL adapter contract

Exact unquoted `:vlax-false` / `:vlax-true` atoms decode to false / true with
status read. Raw serialized values remain intact. Quoted atoms, unknown symbols
and malformed boolean values are invalid_result, never false by default.
Missing, unavailable and unsupported statuses remain distinct. This applies only
to Cell.Empty; literal text cells are not reinterpreted. Existing supported bool
representations remain compatible. Report and TableEvidence versions are unchanged.
