# FIELD graph evidence v1

## Contract

Report 2.8-field-graph-evidence-v1 / FieldEvidenceVersion 2 adds FieldGraphVersion 1.
The authoritative carrier and root code remain intact. Each FieldNode is an
independent entget observation, qualified by carrier, drawing, project and report
hash. Ordered child IDs come from the FIELD header DXF 90/360 region, references
from 97/331. Later cache DXF 90 values are not child counts. DXF 2/3 are concatenated
only in the code header. Parent edges retain child index; identical code is never
an identity key. Root discovery for text uses its extension dictionary ACAD_FIELD,
TEXT entry, not a parsed _ObjId expression.

Source: Autodesk FIELD DXF reference:
https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-DXF/files/GUID-51B921F2-16CA-4948-AC75-196198DD1796.htm

## Invariants

Adapter independently checks node uniqueness, root existence, child counts,
reference counts, reachability, type and traversal completeness. Every graph edge
comes from a recorded child ID. _FldIdx is resolved only to the indexed real node.
Object references retain database handles but do not invent INSERT parent paths.
Graph completeness is acquisition completeness, not complete engineering provenance.
Evaluation DXF 95 remains raw. No binding, scope, semantic or quantity admission.

## Failure / adversarial matrix

Missing graph (including 2.7), missing ID/object, wrong type, duplicate identity,
cycle, count mismatch, malformed record, unvisited node or depth/node limit:
graph_complete=false with reasons. Exporter maximum depth=16, nodes=1024;
adapter independently enforces these limits. Unknown versions cannot claim complete.
No report is rewritten and no Field is evaluated or updated.

## Acceptance

Positive one/many/nested children and DXF references; adversarial variants above;
old 2.7 root-only remains readable and incomplete; existing Field/TABLE/MTEXT/layout,
Discovery, Runner, SHADOW and Test15 remain unchanged in behavior. Real-host
acceptance requires a NEW byte-identical Shadow copy and NEW 2.8 report. Synthetic
tests do not establish AutoCAD support. Existing 2.7 report/manifest remain frozen.
