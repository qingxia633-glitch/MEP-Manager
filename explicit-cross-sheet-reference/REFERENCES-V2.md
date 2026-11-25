# Explicit Cross-Sheet References v2

## Research Gate (reuse existing research)
- Native mechanism: Drawing != Layout != Sheet. Layout targets retain their own
  native identity and parent Drawing; a label is not a Sheet Set approval.
- Authoritative evidence: existing category B Autodesk mechanisms in
  [Drawing identity](../drawing-sheet-identity/README.md), not engineering rules.
- Current project evidence: [Registry v2](../project-drawing-registry/REGISTRY-V2.md)
  supplies role-qualified typed candidates and independently versioned provenance.
- Known boundary: Registry v2 currently emits no independently approved logical
  identity. Its production results cannot yield supported links in this release.
- Minimum safe next step: reuse v1 extraction and source IDs, consume native v2
  lookup results without flattening Layouts, expose resolution separately.

## Contract
ExplicitCrossSheetReferenceVersion=2 requires Registry v2. No implicit migration.
`scan` validates canonical Registry v2, invokes unchanged v1 extraction with an
empty target index, and retains source-only fields. That temporary v1 extraction
view is NOT used for target lookup. All target resolution uses Registry v2 lookup.
`resolve_v2.py` verifies pinned registry bytes and manifest v2/current report
bytes, completion/read errors, and uniquely registered source identity. Output is
exclusive-create. No CAD/report contract change and no historical output rewrite.

## Invariants / failure
Reference IDs are the exact v1 source IDs, with no registry version/target inputs.
Drawing-number references query only drawing_number_candidate; title references
only drawing_title_candidate; filenames only source_filename/filename_stem.
No role fallback occurs. Unknown roles may query a bounded identity-role set but
are marked weak. Target kinds are explicitly Drawing/Layout, never Sheet/View.
Caller kind filters can narrow this set, never expand it or imply source approval.
No identifier -> no lookup. Zero matches -> unresolved; multiple -> ambiguous;
conflict -> conflicting. Partial source cannot yield a link. Unique unapproved
target -> candidate. Layout identity is not replaced by its parent Drawing.
Same S/equipment/style are not new source heuristics. MLEADER/Field remain within
v1 extraction limits. No quantity, Gate, Circuit Trace or Note Scope.

## Supported policy versus production capability
The pure `decide_resolution` policy has a synthetic supported test: supported
explicit source, one typed target, supported logical identity plus independent
identity-support record bound to that exact project/target/parent/alias and source
hash. Status text alone, foreign records or a weak source role cannot support.
For a Layout target, unresolved Sheet identity also blocks supported emission,
even if its logical identity is asserted supported. The synthetic positive supplies
both identity levels; real Registry candidates never acquire these flags here.
This is a software decision contract, NOT an authority importer or authentication.
Production target construction sets identity_support=null: current Registry v2
has no authority contract. CLI accepts no override to inject such a record.
Consequently the synthetic supported policy is tested, but native production
supported emission remains unavailable pending an independently approved Registry
authority contract. No real BX link is counted from synthetic or probe inputs.

## Outputs and counters
`source_references` and `resolutions` are separate. Every typed target includes
project, kind/id, parent Drawing, optional Layout, matched aliases/roles, evidence
status, logical/Sheet state and provenance. Repeated alias evidence is retained.
`references_with_explicit_identifier` counts source number/filename identifiers;
title phrases are separately counted as identifier candidates, not approved IDs.
`source_identifier_insufficient_count` includes missing identifiers and unmatched
title-only candidates; registry_zero_match_count separately records executed misses.
Hit counts count references with each target kind, not aliases. No first-match wins.

## Acceptance
Version refusal; unchanged v1 and source IDs; role/kind filters; Layout candidate;
independent synthetic support policy; drawing+layout/two-layout ambiguity;
conflict; partial source; no-identifier/no-lookup; forbidden implicit links;
canonical index validation; deterministic ordering and immutable source inputs.
Run v1/v2, Registry, Drawing Identity, Field Graph, Discovery current/legacy,
Runner/SHADOW, Test15 and protected hashes. Real probes stay outside BX corpus.

CLI: `python -B explicit-cross-sheet-reference/resolve_v2.py --input-map <private-map> --output <new-json>`.
Input-map fields: project_id, registry_path, registry_sha256, inputs containing
report_path and manifest_path. Private paths/reports are never committed.
