# Field Provenance v0.1

Current extension: [FIELD graph evidence](FIELD-GRAPH.md), report
`2.8-field-graph-evidence-v1`, FieldEvidenceVersion `2`. The sections below describe
the retained 2.7 root-only contract. New graph evidence is additive; 2.7 reports
explicitly have missing/incomplete graphs and are never silently upgraded.

## Contract

Exporter `2.7-field-provenance-v1`, FieldEvidenceVersion `1` adds getter-only
observations. Independent `field_evidence` is an evidence collection, never an
annotation, semantic approval, scope, dependency graph or quantity input.
The authoritative carrier and its raw text/cell identity remain unchanged.

Identity includes project, drawing, snapshot, full carrier path/handle, TABLE
row/column when applicable, and field_index. ObjectID is session evidence, not a
persistent handle. No content_index is invented for the unsupported multiple
contents API. Whole-text FieldCode may contain multiple/nested fields: index 0
identifies the acquired expression envelope, not an enumerated individual field.

## Invariants / failure

Display, source expression, references and evaluation remain distinct. Missing
code stays missing. Unknown/failed getters never establish absence or authored
static text. Old 2.6 Field markers remain display-only evidence. Mixed text is
not split. No nearby-object or string matching is used to establish a source.
TEXT/MTEXT/ATTRIB raw text is retained as carrier_text_observation; it is not
claimed as an evaluated display. Their displayed_value remains unresolved.
Raw DXF reference handles are partial identities until their complete instance
path is established. Evaluation is unsupported, not inferred from displayed text.
No full expression parser or evaluator; classification stays unknown_field.

## Acceptance / adversarial matrix

- Exact code and display retained separately; malformed serialization/duplicate
  keys/unbalanced markers -> invalid_result, no inferred reference.
- Same display at different cell/path/snapshot -> different identity.
- Missing/foreign carrier/version -> unresolved/unsupported, no source approval.
- 2.6 compatibility, TABLE identity unchanged, no Discovery binding/scope.
- TABLE, MTEXT, TextLayout, Discovery current/legacy, Runner, real SHADOW and
  Test 15; compare existing evidence hashes, never rewrite frozen expected.
- Real 2.7 manual-host acquisition is required before claiming BX FieldCode
  support. Synthetic tests establish software contract only.

## Acquisition sources and limits

TABLE GetFieldId returns an ObjectID; the in-process document ObjectIDToObject
and entget chain attempts read-only FIELD recovery. FIELD DXF 2/3 code fragments
and 331 references are retained in order; children are not recursively expanded.
TEXT/MTEXT use the documented FieldCode getter, with raw strings preserved.
ATTRIB is capability-limited; raw field markers can be observed but no undocumented
FieldCode method is presumed supported. No updates, evaluation, save or regeneration.

Autodesk references:
- https://help.autodesk.com/cloudhelp/2026/DEU/AutoCAD-ActiveX-Reference/files/GUID-5AA26AA4-3288-4F2C-A537-3EC995CA5FD0.htm
- https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-DXF/files/GUID-51B921F2-16CA-4948-AC75-196198DD1796.htm
- https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-ActiveX-Reference/files/GUID-FE0C5004-B723-4AE8-888A-7DF11C765C89.htm
