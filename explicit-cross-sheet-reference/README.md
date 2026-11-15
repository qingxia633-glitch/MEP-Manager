# Explicit Cross-Sheet References v1

## Contract

Verified native report + explicit project + pinned Registry v1 -> source reference
observations -> public `registry.lookup` -> target candidates. Independent
ExplicitCrossSheetReferenceVersion=1; no CAD report/version/admission changes.
`resolve.py` takes a private input map and exclusive-create output path. The map
contains project_id, registry_path, registry_sha256, and inputs (report_path,
manifest_path). Every input must uniquely match a registered acquisition's full
report identity and hash. Source DWG/report files remain read-only.

## Invariants

Source extraction, identifier establishment, lookup, and resolution are distinct.
Source reference ID hashes project, source acquisition, carrier/subelement identity,
cue occurrence/span, type, original text and identifier; NEVER target lookup results.
Same identifier in different carriers retains independent provenance. Identical
observations deduplicate; contradictory content at one full carrier/subelement
identity blocks all its references. Order is deterministic.
Conflict keys use paragraph index, excluding content-derived span; source spans
remain in provenance and reference IDs. Changing text length cannot hide conflict.

No geometry, equipment, layer, color, linetype, bare S or similarity creates a link.
Classic Leader v1 is independently revalidated only as a source-side relation.
MLEADER text is partial; no new content/target chain semantics are implemented.
No Xref links, layout expansion, OCR, Gate, quantity or rule approval.

## Minimal support / failure matrix

| Source | v1 behavior |
|---|---|
| TEXT / ATTRIB | decoded explicit cue, full identity/provenance; ATTRIB owner retained |
| MTEXT | existing ordered paragraphs; formatting/unknown escapes retain partial status |
| TABLE cell | text observation; Field display never treated as authored static text |
| FIELD graph | reparse actual FIELD records; SheetNumber/SheetTitle/SheetView/ViewNumber/ViewTitle tokens are partial property candidates only |
| Classic LEADER | validated source relation attached to text; cannot upgrade target |
| MLEADER | partial raw content only |

Lexical cues: 详见, 参见, 详图见, 做法见; standalone 见; 按...图. Plain 见
inside words (e.g. 意见) is not a cue. Numbers use a narrow leading ASCII
prefix-number grammar. Punctuation/space/dash/dot are never deleted to force a
match. Multiple directly listed numbers are separate occurrences. A whole target
phrase ending 图/大样 may be a title candidate. Unknown phrases keep identifier
unresolved. No fuzzy lookup or registry-driven identifier invention.

Registry lookup is restricted to its existing filename/stem/number/title aliases.
Missing target -> unresolved_target; multiple -> ambiguous, never first-match.
One match -> unique_candidate_match, retaining alias strength. Registry v1 has no
independent approved logical-identity contract, so supported_identity_match is
NOT implemented and resolved_links stays empty. Forged approval flags cannot
upgrade this. Self references remain local_reference_candidate, not A-to-B.
Unverified source/identity, malformed graph or missing provenance fails closed.

## Acceptance

Synthetic positive/negative cases exercise each boundary; synthetic Field tokens
do not demonstrate real SheetSet host support. BX reports are scanned anew without
handle-based expectations. Registry, Field graph, Discovery current/legacy,
Runner/SHADOW, Test15 and protected hash checks remain separate evidence.

## Design basis (software architecture, not engineering rules)

Autodesk distinguishes selected SheetSet properties from contextual placeholder
fields: https://help.autodesk.com/cloudhelp/2022/ENG/AutoCAD-Core/files/GUID-D32A29E7-7B98-4ADB-BF32-5CC24DBCC8C3.htm
Sheet/view fields can carry an explicit hyperlink:
https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Architecture/files/GUID-9CA03795-0964-460C-903F-C83B342B3C30.htm
v1 does not claim a complete SheetSet FieldCode parser or evaluate those fields.
