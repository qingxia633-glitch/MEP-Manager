# Layout-qualified Registry v2

## Research Gate (reuse existing research)
- Native mechanism: Drawing File != Layout != Sheet. Layout.Block owns a space;
  Model inventory is not a sheet. Sheet Set association is separate evidence.
- Authoritative evidence: category B Autodesk sources already documented in
  [Drawing Sheet Identity](../drawing-sheet-identity/README.md). These native
  mechanisms are not engineering rules. No new CAD behavior is introduced here.
- Current project evidence: verified ModelSpace reports, owner-fixed 2.9 Layout
  sidecars and DrawingSheetIdentityEvidence/1; no new acquisition.
- Known boundary: no independent Sheet Set authority. Label observations are
  candidates, not approved Drawing/Sheet identities.
- Minimum safe next step: qualify registry candidates by existing native Layout
  identity; expose explicit role/kind filters without semantic propagation.

## Contract
ProjectDrawingRegistryVersion=2 (`registry_version=2`). CAD versions unchanged.
`registry_v2.build_registry(project, inputs)` uses the unchanged v1 acquisition
entry. `migrate_v1(registry)` also accepts stored v1 output, retaining the original
Drawing records and recording source content hash. Migration validates identity,
layout membership and provenance consistency; it does not authenticate authors or
reacquire bytes. Runtime acquisition remains the stronger verification path.
`resolve_v2.py` exclusively creates a new JSON file; never rewrites v1.

## Invariants
Layout ID hashes project + drawing instance + name + native layout/block handles.
It excludes number/title/revision and sidecar content hash. Sidecar snapshot hash
is retained as provenance, not used to turn changed labels into a new Layout.
Model is inventory only. Missing Layout input means not_supplied, not zero layouts.
Each role remains distinct; unknown roles are never copied into Drawing/Sheet roles.
Revision observations remain separate. Layout names are native aliases, not titles.
Sheet candidates exist only for explicit sheet-role evidence; they are never approved.
Every lookup exposes typed targets and evidence. It never returns approved identity.

## Failure / ambiguity
Reject malformed versions, foreign drawing/layout/carrier identity or provenance,
missing required source hashes and malformed filters. Exact duplicate observations
deduplicate; contradictory number/title values within one Layout produce conflict.
Broad queries with multiple typed targets are ambiguous; never auto-select first.
No separator deletion, proximity, similar equipment or engineering inference.

## Cross-Sheet compatibility
Unchanged Cross-Sheet v1 rejects Registry v2. `legacy_view(v2)` returns the explicitly
retained original v1 drawing-only interface; it does NOT flatten new Layout targets
into Drawing aliases. Replay through this view checks legacy behavior only, not
Layout-qualified cross-sheet support. Native v2 lookup is tested separately.

## Acceptance
Synthetic tests cover identity stability, role/kind filtering, missing inputs,
conflict/dedup, Model isolation, foreign identities and legacy compatibility.
Real BX results are derived from current verified inputs, not hardcoded handles.
Run Registry v1/v2, Drawing Sheet Identity, Cross-Sheet, Field Graph, Discovery
current/legacy, Runner/SHADOW, Test15 and protected file hashes. No formal quantity.

CLI: `python -B project-drawing-registry/resolve_v2.py --input-map <private-map> --output <new-json>`.
For stored v1 migration use `--v1-registry <file> --v1-sha256 <hash>` instead.
Input map/source paths remain runtime-private and are not committed.
