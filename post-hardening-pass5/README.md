# Pass 5: conditional provenance roots

Baseline: cb6dd80ed9018383f9112da1ffed14d74761c717.

Contract: ProvenanceRecordContract/1 applies to every admission-critical root.
Required roots are always checked. Conditional roots, when present (not null),
are checked before walking their children. Missing/null correction evidence keeps
the existing no-correction meaning; an empty object is not absent evidence.

Invariant: deleting root provenance cannot remove that root from admission.
Invalid sources, foreign identity, unresolved status and mismatched hash/reference
fail closed at the direct Builder entry; no returned quantity and no input mutation.
No new schema/version or engineering interpretation is required for this bug fix.

Matrix: root provenance missing (with unused source removed), [{}], foreign path,
unresolved status, incorrect source/hash/reference, empty root, valid build,
unchanged native replay, changed provenance with unchanged quantity -> mismatch.

Inspection of conditional roots: measurement_rule already calls check(root);
reviewed CAD conversion already calls check(root). Correction evidence was the
only walk-only conditional root. Recursive arbitrary metadata is not promoted
into new admission roots in this pass.

Validation: new tests first, then Pass 4 provenance/authorization/assumption/replay,
Builder current-contract, source-backed, Test 15, private Golden and frozen hashes.
No historical fixtures/expected changes and no commit/push or quantity issuance.
