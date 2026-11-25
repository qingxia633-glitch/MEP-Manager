# Targeted Native Association Probe v0.1

Independent, getter-only AutoLISP acquisition. No semantic resolver, rule approval or quantity.

## Read-only correction (collector_revision 2)

Follow-up revision 3: the second real run kept DBMOD zero through idle control, load, helpers, the seed's entity/XData and owner reads, then changed during an ENTGET made by the ENAME serializer. `target_context` identifies the active seed, not necessarily the referenced object. The precise referenced handle was not logged and the host's internal cause is unconfirmed. Revision 3 removes database access from serialization: already-read ENAME/handle pairs are cached, otherwise the value is an object with `reference_status=unresolved_not_dereferenced` and a report-session token. That token is not a stable handle or cross-report identity. Explicit scoped reads still use guarded getters. Getter arguments are also recorded as session tokens for diagnosis. Both rejected real reports remain immutable; success requires a new clean-copy run and unchanged DBMOD throughout.

The first real report is retained as rejected evidence: DBMOD changed from 0 to 1. Its disk DWG hash matched, which does not prove unchanged in-memory state. The root cause is **not established**. Source audit found no GetExtensionDictionary, regapp, entity mutation, XData write or dictionary-creation call. The EffectiveName ActiveX path remains a diagnostic suspect, not a confirmed cause.

Autodesk documents that [GetExtensionDictionary creates a dictionary if absent](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT-ActiveX-Reference/files/GUID-87411ABA-ABCF-45AF-A8C5-0ED036A34D5F.htm). This collector does not call it. Existence is derived solely from the balanced native 102 ACAD_XDICTIONARY / 360 section; absent stays absent and malformed/unavailable stays unavailable.

Revision 2 records DBMOD around acquisition getters, effective-name conversion/get/release, GROUP queries and report serialization. The independent trace includes idle control, loading and helper checks. The first changed getter stops execution without SAVE, UNDO or state reset. A dirty or incomplete trace rejects revision-2 CLI verification, even if report footer values appear clean. Host control observations do not prove causality; a changed stage requires review of its specific call.

BLOCK begin and BLOCK_RECORD are distinct: `block_begin_handle` is validated against native type BLOCK; `block_record_handle` requires native type BLOCK_RECORD, matching definition name and the BLOCK begin's unique owner outside reactor sections. Both raw records are preserved. Unconfirmed BTR remains null/unresolved. The existing `insert` field is retained alongside `insert_handle`, `block_name`, `effective_block_name`, traversal provenance and identity status. Raw transforms remain uncomposed.

The rejected report identified the BLOCK begin as the block record. The accepted revision 3 acquisition independently read the begin and its owner, checked both native types and the definition name, and recorded DBMOD zero throughout.

## Contract / invariant / failure / acceptance

Input: explicit project, expected full Shadow DWG path, nonempty unique hexadecimal seed handles, new JSONL output path. An external request pins actual DWG bytes before acquisition; the validator rechecks bytes after acquisition. The LISP does not claim to hash DWG bytes.

`TargetedNativeProbe/1` JSONL contains header, raw typed DXF node records, typed reference observations, group membership records, gaps, and footer. Numbers with AutoLISP REAL type are decimal strings (12 decimal precision); original DXF types accompany values. ENAME values become stable handles, not transient process addresses. Native raw data remains authoritative. No effective geometry/semantic interpretation is manufactured.

Owner is the single 330 outside 102 groups before subclass data; reactors and extension dictionaries retain their named 102 section. Unknown/malformed sections remain unresolved. 340 on GROUP is membership, 340 on LEADER is annotation, 340 on MLEADER is not automatically either. No reference constitutes engineering applicability.

Limits: 256 queued/read nodes, depth 8, 512 block/attribute subentities, 10000 GROUP-index entries. Dedup does not erase relationship observations. Repeated references terminate by visited handle, with path/reference edges retained; a limit/error/proxy produces incomplete coverage. Shared definition data is stored once; its INSERT references preserve the instance paths needed for later transform composition. No WCS terminal matching is implemented here.

Reverse GROUP query is scoped to the requested seed handles. Arbitrary incoming XData/dictionary references, nested instance occurrence enumeration and visual arrow target inference are **not** complete. Therefore no automatic `not_found` result or semantic supported status is emitted. MLEADER raw context is preserved, interpretation remains unresolved.

New output only; Unicode LISPSYS 1/2 required; no drawing writes, save, setvar, entity mutation or view changes in collector. DBMOD before/after is checked but is not proof by itself: external DWG hashes must also match. Unsupported host functions or object types must not be hidden by a complete marker. Host execution and software validation are separate acceptance stages.

## Research basis (Autodesk mechanism, not engineering rules)

Reuse existing block-probe and Layout owner/reactor research. Missing API mechanisms checked:
- [XData retrieval / wildcard applist](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT-AutoLISP/files/GUID-1A2A0518-E9DB-462E-925E-32181D96CE4D.htm)
- [GROUP member 340](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-5F1372C4-37C8-4056-9303-EE1715F58E67.htm)
- [Owner/reactor/extension sections](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-6939D69E-04CB-4F4C-87B2-67BC540FCF58.htm)
- [LEADER annotation 340](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-396B2369-F89F-47D7-8223-8B7FB794F9F3.htm)
- [BLOCK definition first entity -2](https://help.autodesk.com/cloudhelp/2015/CHS/AutoCAD-AutoLISP/files/GUID-1720D8DC-5559-4AC1-8A75-3C932834D77C.htm)

## Run

Load `TargetedNativeProbe.lsp` in the already opened byte-verified Shadow copy. Call `(tnp:run handles project expected-dwg-path new-output-path)` with a list of handle strings. `MEPTARGETPROBE` prompts for the same parameters. Do not use authoritative original DWG. Manual command supplied in the local run instructions.

After host execution: `python -B targeted-native-probe/verify.py --report FILE --request REQUEST --output NEW_DIRECTORY`.
Request: `project_id`, `drawing_path`, `dwg_sha256_before`, `seed_handles`. Output: normalized evidence + independent manifest v2 (`report_format=TargetedNativeProbe/1`, not the existing full-report manifest identity schema). Hash scope is exact completed report bytes; no self-referential report hash.

## Tests / matrix

Software tests cover owner/reactor, malformed sections, typed reference roles, missing seeds, wrong drawing/project, dirty DBMOD, incomplete/truncated output, duplicate nodes, hash mismatch, absent-vs-unread XData, incomplete coverage and no semantic approval. Static LISP checks are not a real AutoCAD execution. `HostTests.lsp` provides in-host pure-function tests. Actual collector must still be exercised against the byte-pinned copy before native evidence can be claimed.
