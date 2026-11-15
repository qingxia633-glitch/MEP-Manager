# Drawing / Sheet Identity Evidence v1

## Research basis

Autodesk Layout separates layout settings from its Block entity container:
https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-ActiveX-Reference/files/GUID-EFC848F1-26BE-4EFA-BC0E-11F874D73842.htm
Layouts contain paper-space entities and viewports; a DWG may contain several layouts:
https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-Core/files/GUID-93E88E2A-3BA8-40C1-8BF5-9A50B716EB34.htm
GetAttributes returns instance references; GetConstantAttributes returns definitions:
https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-ActiveX-Reference/files/GUID-3E8E1756-F45D-4CCE-838B-00FBC0374278.htm
https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-ActiveX-Reference/files/GUID-2655DC82-1DD4-42EC-888C-5F6E32A7342B.htm
Sheet properties and contextual placeholder fields need real Sheet Set association:
https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-Core/files/GUID-3B0D3681-07BB-4B51-98CE-EB3C996771EB.htm
https://help.autodesk.com/cloudhelp/2022/ENG/AutoCAD-Core/files/GUID-D32A29E7-7B98-4ADB-BF32-5CC24DBCC8C3.htm
These are category B native mechanism sources, not Chinese engineering rules.

## Contract

DrawingSheetIdentityEvidenceVersion=1 consumes a hash-pinned, completed layout
sidecar produced in the same new Shadow DWG as a verified ModelSpace report.
Layout CAD ReportVersion=2.9-layout-identity-v1 is independent of RegistryVersion=1
and the unchanged ModelSpace exporter 2.8. No PaperSpace entities enter the
ModelSpace parser. The sidecar includes Model layout inventory only, and each
PaperSpace Layout's top-level entities, attached ATTRIBs and direct constant ATTDEFs.
Nested blocks/Xrefs are not expanded. The helper reuses read-only entity/Field getters.

Input Registry item adds layout_report_path and layout_report_sha256. The full DWG
reference must equal the ModelSpace report reference. SHA-256 pins exact sidecar
bytes; it does not authenticate CAD or a human decision. Source DWG bytes must be
verified by the Registry input. Layout handles, block-record handles and names
qualify identities by project and acquisition instance; child attributes retain
their INSERT owner and complete parent_path. Missing order stays null.

## Invariants

- Drawing File != Layout != Sheet != View; a viewport is not a sheet.
- Old ModelSpace-only reports mean layouts not acquired, never no layouts.
- PaperSpace INSERT plus at least two metadata roles including number/title is
  candidate_title_block, not an approved frame. Position/name/size alone never suffice.
- ATTRIB values are instance evidence; constant ATTDEF values remain separate
  definition/default evidence and never replace instance values, including blank values.
- Drawing/sheet numbers and titles are separate. Generic NO/NUMBER/TITLE retain
  identifier_role=unresolved. Filenames remain source aliases, never title evidence.
- Field properties require a matching carrier and complete reparsed FIELD graph.
  Tokens are property candidates only, not proof of current-sheet association.
- Revision fields remain observations; DATE alone is not revision_date. Hashes
  never become formal revisions. No inferred Rev A/B.
- Distinct values for one role in a layout are conflicting; multiple carriers or
  identical numbers across layouts remain ambiguous. No first/strongest auto-winner.
- No Sheet Set reader/dependency in v1: evidence is unavailable, not proven absent.
  Explicit title-block approval and supported sheet identity are not emitted in v1.
- No engineering semantics, quantity, rule approval or A-to-B links. Existing
  cross-sheet resolver is replayed unchanged and cannot emit supported links.

## Failure

Reject missing/changed hashes, foreign drawing references, unsupported versions,
incomplete envelopes/counts, missing/duplicate layout or entity identities and
inconsistent owner/space membership. Unreadable layout inventory fails closed;
per-layout entity errors remain unavailable, never interpreted as empty.
Malformed Field graphs cannot strengthen identity. Unknown roles preserve values.

Owner extraction contract marker LayoutOwnerContractVersion=1 requires the owner
330 outside all DXF 102 groups, before the first subclass marker, and a resolved
BLOCK_RECORD type. The first 330 may be a persistent reactor, not the owner:
https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-3610039E-27D1-4E23-B6D3-7E60B22BB5BD.htm
The initial real report without this marker was rejected and preserved; use the
new owner-fixed report, never patch raw acquisition bytes. Host self-tests cover
reactor/owner separation and duplicate owners.

Unchanged Cross-Sheet v1 accepts only its old alias kinds. Revision, generic roles
and sheet_title_candidate stay in the independent evidence object. Ambiguous or
conflicting whole-drawing identities are not projected to new flat aliases. Actual
carrier snapshot remains the sidecar hash; source_identity on projected aliases
is explicitly the Registry acquisition attachment, with both report provenances.
This adapter does not approve a logical identity or hide the actual carrier.

## Acceptance

Tests cover two layouts, legacy unknown coverage, owner/space isolation, ATTRIB
versus ATTDEF, label roles, Field provenance, duplicate/conflicting candidates,
project isolation, filename/revision boundaries, Registry integration and no links.
Use new real Shadow copies and exclusive report destinations; preserve originals
and frozen outputs. Report actual host coverage separately from synthetic tests.
Run Registry, Cross-Sheet, Field Graph, Discovery current/legacy, Batch/SHADOW and
Test15 without changing historical expected values.
