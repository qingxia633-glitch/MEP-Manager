# Linetype definition evidence v1

Contract: a separate, targeted ModelSpace drawing sidecar supplies named LTYPE records. The existing full-report version and raw entity and layer styles retain their contracts. Input names come from verified top-level entity style evidence. Preserve each entget group in order, including repeated codes and unresolved session-local ENAME tokens. Only group 340 may trigger a guarded STYLE record read. The queried symbol and the referenced STYLE must have distinct, verifiable native identities.

Invariant: a definition belongs to its drawing bytes, project and snapshot. A top-level explicit or qualified ByLayer occurrence can look up a same-source definition. ByBlock, unresolved inheritance and nested occurrences stay unresolved. A group 9 on a valid text element supplies lexical evidence. Pattern repeats, symbol names and proximity grant no additional entity identities, circuit, specification or quantity.

Failure: reject mismatched document, request, drawing bytes, snapshot, version, DBMOD, stage sequence, duplicate identities or unfinished capture. Preserve malformed and unknown pattern data as partial with reasons. Missing definitions remain unavailable. A result file from an aborted host run is diagnostic only.

Acceptance: verify the pinned source bytes, the Shadow before/after, host stages, exact requested record inventory, ordered element count and valid STYLE links. Reconcile lexical evidence per native entity independently. Software fixtures exercise parsing, isolation and fail-closed cases. Real validation requires a completed separate manual-host capture.

## Operation

Create a new byte-identical Shadow. Pin its pre-open SHA-256 and the verified full report and manifest in a local request. Use the actual raw entity/layer linetype names from that report. Keep the request and both source DWG paths for external validation. The local wrapper records DBMOD before/after loading the targeted probe helpers and this collector, invokes `ltd:run` once for the list, then records DBMOD after closing the output. Use new paths for each attempt. A nonzero baseline or any change aborts acceptance.

After closing the capture, run `python -B project-evidence-discovery/verify_linetypes.py REQUEST.json CAPTURE.jsonl NEW-RESULT.json`. The verifier rehashes sources and checks the exact request and host trace. The result includes native raw triples, per-definition parsing status, per-entity links and acquisition hashes. Inspect missing definitions and partial elements independently of session integrity.

Autodesk documents repeated group 49, complex bit flags and group 340. The group codes for embedded text/shape cannot all be obtained from tblsearch/tblnext. Use tblobjname and entget. Group 50 is in radians. Optional values stay absent. The sidecar uses the targeted probe's getter/DBMOD and typed triple serialization, including its decimal representation of REALs. Unresolved ENAME tokens are not persistent IDs. [LTYPE (DXF)](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-DXF/files/GUID-F57A316C-94A2-416C-8280-191E34B182AC.htm)
