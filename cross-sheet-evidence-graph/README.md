# Cross-Sheet Evidence Graph v0.1

## Research Gate: reuse existing research
- Native mechanism (B): Drawing != Layout != Sheet. Reuse
  `drawing-sheet-identity/README.md`; no new CAD behavior or acquisition.
- Basis (B): existing Autodesk identity mechanisms, not engineering rules.
- Current evidence (E): `explicit-cross-sheet-reference/REFERENCES-V2.md` and
  `project-drawing-registry/REGISTRY-V2.md`. The current Registry has no approved
  Sheet authority importer; Graph cannot supply one.
- Boundary: missing source identifiers and exact registry misses remain distinct;
  ambiguity/conflicts remain observations. No identity inference or new lookup.
- Minimum step: lossless, typed evidence graph over pinned References v2 output.

## Contract / trust boundary
`CrossSheetEvidenceGraphVersion=1`. `build_graph(document, source_sha256)` consumes
References v2 with Registry version 2 and returns nodes, edges and per-reference
records. `resolve.py --input FILE --sha256 HASH --output NEW_FILE` hashes actual
input bytes, rejects duplicate JSON keys/nonfinite numbers, validates before
exclusive output creation. Hashes pin bytes; they do not authenticate approval.
The pure entry accepts a caller-supplied digest; only the file entry verifies bytes.

Source and resolution objects are copied unchanged into each record. Auxiliary
source conflicts/exclusions and top-level provenance are retained. Input summary
and duplicated status groups are not authoritative; graph statistics come from
validated source/resolution pairs. Resolution is recorded, not approved by Graph.
The existing pure v2 decision contract checks status consistency without running
extraction or Registry lookup. No Graph output is Gate/quantity authorization.

## Invariants
- Reference node identity depends on project + source reference ID, not target.
- Identifier nodes are reference-qualified; same text never merges references.
- Target nodes contain identity only. Alias/status/provenance stays on each
  reference's candidate edge and full resolution record, avoiding strongest-wins.
- Drawing/Layout IDs are type-qualified. Layout retains parent Drawing; no
  Layout-to-Sheet conversion. Sheet nodes are unsupported by the v2 producer;
  unknown target kinds are rejected, never silently mapped. Sheet state remains
  raw metadata on candidate evidence, not an inferred Sheet identity.
- Full source parent_path, carrier/subelement identity and source provenance stay
  in records. No paragraph/Field/carrier normalization or semantic propagation.
- Ordering is deterministic; exact duplicate source/resolution pairs deduplicate;
  contradictory duplicate IDs are invalid input. Upstream conflicting resolutions
  and their evidence are preserved rather than resolved.
- `unresolved_reasons` preserves upstream reasons; separate diagnostic counters
  identify missing identifiers and exact lookup misses without inferring scope.

## Failure / acceptance
Reject bad versions/types, missing identities/provenance, foreign project,
orphan/missing resolution, inconsistent status/lookup, invalid typed target,
duplicate target and output overwrite. No default parent_path or provenance.
Synthetic tests cover positive recording, ambiguity/conflict, identity separation,
missing versus zero match, determinism, immutability, invalid inputs and CLI pinning.
Then read existing BX output, verify every source/resolution round-trip; synthetic
cases/probes never contribute to real coverage. Run related current suites,
SHADOW, classified legacy, Golden checks, Test15 and pre-change file hashes.

Out of scope: source extraction, identity approval, Entity Resolution, CAD
acquisition, Gate, engineering semantics, scope, topology and quantity.
