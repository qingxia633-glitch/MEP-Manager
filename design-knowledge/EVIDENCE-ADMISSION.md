# Design evidence admission — experimental

## Boundary

`EvidenceAdmission.psm1` consumes an automatic DesignStatementBridge result. It never changes the reader, paragraph, hierarchy, statements, raw snapshot, or existing ModelCore consumers. Records are not executable rules. `Test-DesignEvidenceUse` is the explicit future consumer guard: only candidate-context use in the same source scope is permitted. A request for an instance application, other snapshot/sheet, or a specific system when evidence identity is unknown returns false.

The seven supported use names have separate decisions, reasons, and restrictions. `support_information_requirement` means supporting an investigation or documenting a missing fact; it cannot mark a requirement satisfied. Rule matching means candidate retrieval, not evaluating a physical line against a condition. Device-role and system-identity permissions remain blocked because this adapter does not validate those semantics or resolve system scope.

`admissible_candidate` is reserved. This version deliberately produces no such upgrade: it lacks an independently validated applicability evaluator. Even a future admissible record must obey the permanent prohibitions on instance assignment, network creation, quantities, and RawEntity modification.

## Records and gates

- Main `DesignEvidenceCandidate`: source document/snapshot/sheet/column/section/subitem/paragraph/atomic, raw span references and contents, derived meaning, separate semantic/structural/scope/conflict/provenance states, upstream reviews and grouped review references.
- `EvidenceAdmissionDecision`: archived_only, supporting_candidate, admissible_candidate (reserved), blocked; allowed and prohibited uses; per-use reasons, application mode and scope; required review references.
- Provenance checks resolve span references, exact raw-text reconstruction, handle/snapshot/offset consistency, atomic and paragraph membership and sheet identity. They validate the supplied upstream trace; they do not reparse the DWG or re-prove its hierarchy. The runner records upstream artifact SHA-256.
- Empty atomics never become evidence. Unknown statements remain archived_only. Missing provenance or an explicitly supplied snapshot-scoped statement conflict blocks permissions. Structural, semantic, scope, condition, alternative and reference uncertainty remains visible even when narrow context use is allowed.
- References are **separate child facets**. This permits navigation for an independently bounded reference inside an otherwise unknown statement without upgrading its parent. Child spans must lie inside parent spans and reconstruct the reference literally. Target content is always prohibited; unmatched closing parentheses are reviewed.
- Conflicts enter explicitly as `{sourceStatementRef, sourceSnapshot, conflictId}` or a conflicting statement status. `none_reported` means no supplied conflict, not proof of no conflict. HumanConfirmation references are an interface only and never automatically override a conflict.
- Reviews are grouped by source sheet and root reason, retaining affected evidence IDs, source statements and handles. They are not silently resolved.

## Running

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/Read-DesignEvidenceAdmission.ps1 -OutputPath <new-output.json>
powershell -NoProfile -ExecutionPolicy Bypass -File design-knowledge/tests/Test-EvidenceAdmission.ps1
```

The runner defaults to `local_test_data/ew0002-design-statements-reviewed-v2-20260924.json`, refuses to overwrite existing outputs, and does not invoke AutoCAD. The saved real run is `local_test_data/ew0002-evidence-admission-final-20260925.json`.

## EW-0002 real run

Input SHA-256: `AA7ED618121D49A725D17CAB1963F06FCA08DADCCEEA3663033BB870C2345352`.
Source snapshot: `7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F`.

| Record class | Total | archived_only | supporting_candidate | admissible_candidate | blocked |
|---|---:|---:|---:|---:|---:|
| Statement records | 86 | 28 | 58 | 0 | 0 |
| Reference child facets | 3 | 0 | 3 | 0 | 0 |
| Combined | 89 | 28 | 61 | 0 | 0 |

All 9 empty atomics remain review-only. The 28 unknown parents have no allowed uses. No permission allows instance-level application.

| Use | Statement records | Including reference facets |
|---|---:|---:|
| support_search_scope | 58 | 61 |
| support_information_requirement | 58 | 58 |
| support_design_rule_matching | 55 | 55 |
| support_installation_requirement | 1 | 1 |
| support_reference_navigation | 0 | 3 |
| support_device_role | 0 | 0 |
| support_system_identity | 0 | 0 |

Overlapping blockers on 86 main records: semantic_partial 86, scope_unresolved 86, structural_partial 73, structural_incomplete 13, unknown_statement_type 28, clause_scope_unresolved 10, condition_evaluation_unresolved 7, reference_unresolved 3, condition_threshold_unresolved 2, alternative_selection_unresolved 1. These explain restrictions and do not all block candidate-context investigation. Reviews form 12 root groups including blank atomics and reference-boundary uncertainty.

### Golden and reference results

- 4.12.1 A/B retain qualitative short/long conditions. Both support search, information-gap investigation, and candidate rule matching. Thresholds remain unresolved; actual line classification is prohibited.
- 4.12.1 C retains the purpose relation. It supports search/information investigation, not proof that any real breaker meets selectivity requirements.
- `见表4.1`, `见系统图）`, `详见表6.1` are navigation facets. Targets remain unresolved. The second retains `reference_boundary_uncertain`. The unknown parent of the first remains archived_only.

Conclusion: **useful_but_partial**. Next, wire guarded candidate-context search and information-investigation adapters. DeviceRole/SystemIdentity require task-specific scope and semantic validation before permission can be granted. This module does not bypass ModelCore system isolation or its existing supported-evidence checks.

## Validation (2026-09-25)

- All 33 offline regression suites passed. No AutoCAD invoked.
- The final admission-specific test passed 410 checks, including snapshot mismatch, empty/missing spans, raw mismatch, missing paragraph, reference-facet provenance, conflict blocking, serialized permissions, and scope/system isolation.
- Final saved artifact was compared with a fresh adapter result and matched exactly (excluding runner provenance envelope).
- Upstream statement artifact SHA-256 remained unchanged. Generic admission logic contains no fixture handles, golden paragraph ID, or EW-0002 text.
- Output SHA-256: `BC9A8513AC5ACD488E3FDD550640B86359DB3609FC37D7F7E1E951FF20D20FE1`.
