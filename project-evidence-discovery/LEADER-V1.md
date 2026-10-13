# Leader evidence v1

## Contract
Only ModelSpace top-level acquisition. Classic LEADER exports WCS vertices,
arrow flag and resolved annotation handle. MLEADER exports capability results
and raw DXF; embedded text is owned content, not a synthetic TEXT entity.
This is discovery evidence, never project semantic approval.

## Invariants and failure
Version, acquisition scope, empty top-level path, geometry count, arrow and
annotation resolution must all agree before a v1 leader binding is attempted.
Missing/failed/foreign fields remain unresolved. MLEADER branch geometry is not
inferred from raw repeated DXF codes. Legacy records remain readable as unresolved
raw evidence; missing version or acquisition scope does not authorize binding.
No nested, xref, layout or proxy completeness claim. No self-referential hash:
the report is hashed only after writing, in separate metadata.

## Acceptance
Adapter adversaries cover scope, path, version, failed reads, vertex count,
arrow absence and partial MLEADER. Real AutoCAD object acquisition must be
validated separately from synthetic tests and project applicability.

## Report fields / capability
`LeaderEvidenceVersion="1"`, `LeaderScope`, `LeaderParentPath`,
`LeaderCoordinateSystem`, `LeaderGeometryStatus`, `LeaderVertexCount`, repeated
`LeaderVertex_WCS`, `LeaderArrowStatus`, `Arrow_WCS`,
`LeaderAnnotationStatus`, `AnnotationHandle`, `AnnotationType`.
Classic DXF 340 is resolved through entget to a stable handle, never a runtime
ename string. MLEADER getter statuses and raw DXF are retained; branch indices
are not guessed. MLEADER geometry binding remains unresolved in v1.

`report_manifest.py REPORT NEW_MANIFEST [--encoding cp936]` writes an exclusive
sidecar after export. Default UTF-8; old LISPSYS=0 output requires an explicit
encoding, with no replacement decoding. `load_report(..., encoding=..., manifest=...)`
verifies sidecar v2 byte length, SHA-256, filename, encoding and report identity
(drawing, extractor/acquisition metadata and observed leader versions). An absent
manifest yields `report_integrity=unavailable/legacy`; the computed byte hash is
not described as verified. Sidecar v1 lacks the identity contract: retain it,
and create a separate v2 sidecar if current verification is required. Neither
sidecar authenticity nor reviewer authorization is proved by a matching hash.
The exporter does not hash itself.

Both `load_report` and direct `discover` call `leader_contract.py`. Classic v1
requires a first-vertex arrow, finite WCS geometry, matching count and explicit
top-level scope/path. AnnotationType must be TEXT/MTEXT and match the actual
annotation. MLEADER is capability evidence only and does not inherit classic
binding rules. Invalid records retain validation reasons; diagnostics distinguish
missing arrow, nearest distance and ambiguous targets without changing tolerance.

TEXT/MTEXT retain `raw_serialized_text`, `decoded_text`, and `normalized_text`
separately. `report_text.py` decodes only the exporter string escape subset;
unknown escapes remain unresolved. Explicit CP936 decoding is supported; wrong
encoding errors are not replaced or guessed. Leader/binding provenance includes
annotation identity, leader path/version and report/snapshot identity.

The real verifier requires `--manifest`, uses explicit checks under `python -O`,
and never overwrites a source report. See [hardening contract](LEADER-HARDENING.md)
for adversaries and the retained legacy-test boundary.

`tests/validate-leader-acquisition.lsp` is destructive ONLY to an isolated empty
validation drawing: it creates a line, MText, classic leader and MLEADER. Never
load it into a project drawing. It calls the production exporter functions.
Core Console validation is separate from project evidence and cannot approve a
project-specific line identity or rule scope.

## First-round verified support (2026-10-09)

| Case | Acquisition / binding |
| --- | --- |
| ModelSpace classic LEADER -> MTEXT | Real AutoCAD 2021 Core Console chain verified; annotation handle + WCS arrow produce a discovery candidate |
| Classic LEADER -> TEXT | Export path present; no real positive verified this round |
| MLEADER + MText | Native MULTILEADER created/read; raw DXF preserved; ActiveX getters unavailable in tested Core Console; binding unresolved |
| MLEADER block / multibranch | Raw records retained; normalized content/branch binding unverified |
| Nested INSERT / Xref / layouts / proxy | Out of scope |
| Project applicability | Not established by independent validation drawing |

The observed classic object was 279, annotation 277, line 276. These handles
are validation output only and are not used by production code or rules.
The original report bytes are CP936 under this LISPSYS=0 environment; the
explicit encoding is recorded in provenance and the post-write manifest.
