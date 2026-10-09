# Local definition geometry diagnostic

## DefinitionLocal coordinates v1.2

Reload `BlockLocalGeometryProbe.lsp`. Both anchor lookup diagnostics now include
DXF210 and require identical normals as well as identity/owner/points. Raw DXF10,
DXF11 and DXF210 are preserved independently from AnchorPoint_DefinitionLocal.
For TEXT with explicit normal (0,0,1), identity_ocs_to_definition preserves DXF10
without calling trans. This is not an INSERT placement or instance WCS coordinate.
Other supported OCS anchor types (TEXT/ATTDEF/CIRCLE/ARC/INSERT) use the explicit
normal-vector-to-zero trans path; missing/invalid normals stop, without a DXF10
fallback. LINE and MTEXT DXF10 are definition Cartesian and are identified as such,
not falsely marked OCS. Unsupported coordinate semantics stop. LWPOLYLINE raw
two-component DXF10 is not promoted to a 3D anchor without an elevation policy.
Every conversion preserves point/from/to types and values, return value or original
exception text. InstanceWCS is always not_computed for entity anchors.

GetBoundingBox is documented as WCS, not automatically an instance coordinate for
an unplaced definition entity. Before any window comparison, the probe verifies
getter bounds against min/max of all direct, zero-thickness LINE DXF endpoints
in the requested owner block (absolute component tolerance 0.00001). The first
control and every mismatch are reported. No controls, getter failure or mismatch
stops BEFORE window filtering; no guessed translation or INSERT transform is used.
This is runtime evidence about the definition getter frame, not proof of proxy
geometry accuracy, evaluated visibility or instance placement. Controls must be
validated during real AutoCAD acceptance. If the gate fails, the next minimal
unification would be a separately tested DefinitionLocal bounds adapter for known
entity types, leaving unsupported extents unknown; that adapter is not implemented.
The existing bbox overlap predicate, window half-size, and entity exporter are
unchanged. No raw entity is moved or transformed in the DWG.

References: Autodesk TEXT DXF (OCS 10/11 and normal 210), LINE DXF (Cartesian 10/11),
and GetBoundingBox ActiveX (WCS axis-aligned bounds):
https://help.autodesk.com/cloudhelp/2021/CHS/AutoCAD-DXF/files/GUID-62E5383D-8A14-47B4-BFC4-35824CAE8363.htm
https://help.autodesk.com/cloudhelp/2016/CHS/AutoCAD-DXF/files/GUID-FCEF5726-53AE-4C43-B4EA-C84EB8686A66.htm
https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-ActiveX-Reference/files/GUID-A20C361C-BBF0-4EAB-8BE7-709154CEEE09.htm

## Anchor diagnostics v1.1

Reload `BlockLocalGeometryProbe.lsp` after updating. Raw Handle input is retained;
ASCII whitespace is trimmed and case normalized. Direct traversal and `handent`
must resolve the same entity and both owners must match the requested block record.
Neither lookup bypasses ownership. DXF10 is required; DXF11 is diagnostic only.
Console diagnostics precede window prompts and include DWG, version, block record,
both lookup results and AnchorStatus. Successful reports repeat these diagnostics.
Failures stop before opening output; retain command-line diagnostics for review.

Statuses: resolved, handle_not_found, owner_mismatch, missing_dxf10,
coordinate_transform_error, traversal_handent_disagreement. Getter exceptions are
reported with their messages and stop as disagreement, not as a proven absence.
No historical index is overwritten or treated as the current database. Compare
runtime TEXT/Handle/Owner/Text_RAW/DXF10 with the index; differences are snapshot/runtime
discrepancies, not grounds to silently replace source facts. No sample-specific
expected text is embedded in the generic command.

`Test-Anchor.ps1` evaluates the actual pure Lisp decision/normalization forms using
a restricted test evaluator and checks integration contracts. It does not simulate
ActiveX/handent/entget/trans; those still require real AutoCAD acceptance.

Load `BlockDefinitionProbe.lsp`, then `BlockLocalGeometryProbe.lsp` using APPLOAD.
Run `MEPBLOCKLOCALPROBE`. Supply definition name, anchor internal Handle (or blank
for numeric definition XYZ), positive XY square half-size, and window evidence.
Save `block-local-geometry-probe.txt` in a fresh directory; existing files are refused.
The main extractor and existing probe commands are unchanged.

## First manual fixture (not part of generic algorithm)

- Drawing: `PC-B-P01(-1F)-地下室给排水平面图_t3.dwg`
- Definition: `PX-B-P01(-1F)-JSK`
- Anchor: `836` (`K1-4`)
- Half-size: `3000` drawing units; XY square, no Z filter.
- Evidence input: `K1-4; nearest other label K4-5/696 at 10268.351312 drawing units; initial half-size 3000; scope uncertain`
- Index SHA-256: `90954BB823B53B8CD338A4B016BD993D1C39E3875CD6B49A14DE341CB30C59D5`
- Anchor local position: `(555804542.9461051,553211518.1702802,0.000000000028)`.
- Nearest other readable label: `696/K4-5`,
  `(555812305.37007153,553218240.06084955,0)`.

This window excludes other readable pit labels but does not establish the pit
boundary or exclude unlabeled nearby pits. Always `window_scope_uncertain`.
Do not enlarge automatically or import category parameters as instance facts.

## Selection and limitations

Only direct definition entities are traversed. Getter bounding-box overlap is a
conservative spatial filter, not clipping or exact containment. Entity bounds and
anchor are compared in the definition's database coordinate frame; raw DXF may
use entity OCS and is preserved without relabeling it WCS. TEXT anchor DXF10 is
not necessarily its alignment point. Full INSERT DXF records preserve transforms;
referenced definitions are not recursively exported. Getter extents for an INSERT
may encompass its displayed contents without enumerating those contents here.

Unknown extents retain identity and raw fields even if their locality cannot be
established; count them separately. Extent/read failures increment ReadErrorCount.
Proxy/unsupported semantics remain `unknown`. Extents unavailable on a large
definition may therefore produce many unknown-scope records, never silent losses.
DXF60/layer flags do not establish evaluated visibility. Coordinate Z is not an
engineering elevation. No device binding, connection, Circuit or quantity output.

`Test-LocalProbe.ps1` checks static safety/contracts and the real window evidence.
It does not execute AutoLISP or validate AutoCAD GetBoundingBox behavior. Real
AutoCAD export is still required before interpreting pit/pump geometry. The index
contains no geometry that would justify claiming those results ahead of export.
